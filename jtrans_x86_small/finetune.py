from unicodedata import name
from transformers import BertTokenizer, BertForMaskedLM, BertModel
import torch.multiprocessing
from torch.utils.data import DataLoader
import os
import torch
import torch.nn as nn
import numpy as np
from tqdm import tqdm
from data import load_paired_data, FunctionDataset_CL, FunctionDataset_CL_Load
from transformers import AdamW
import torch.nn.functional as F
import argparse
import wandb
import logging
import sys
import time
import data
import pickle
import glob
import json

WANDB = True

def get_logger(name):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename=name)
    logger = logging.getLogger(__name__)
    s_handle = logging.StreamHandler(sys.stdout)
    s_handle.setLevel(logging.INFO)
    s_handle.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s[:%(lineno)d] - %(message)s"))
    logger.addHandler(s_handle)
    return logger

def train_dp(start_epoch, model, args, train_set, valid_set, logger):

    class Triplet_COS_Loss(nn.Module):
        def __init__(self,margin):
            super(Triplet_COS_Loss, self).__init__()
            self.margin=margin

        def forward(self, repr, good_code_repr, bad_code_repr):
            good_sim=F.cosine_similarity(repr, good_code_repr)
            bad_sim=F.cosine_similarity(repr, bad_code_repr)
            #print("simm ",good_sim.shape)
            loss=(self.margin-(good_sim-bad_sim)).clamp(min=1e-6).mean()
            return loss

    if WANDB:
        wandb.init(project=f'jTrans-finetune', name="jTrans_Freeze_10_Train_Test")
        wandb.config.update(args)

    logger.info("Initializing Model...")
    device = torch.device("cuda")
    model.to(device)
    logger.info("Finished Initialization...")

    seed = torch.randint(0, 2**32 - 1, (1,)).item()
    torch.manual_seed(seed)
    train_dataloader = DataLoader(train_set, batch_size=args.batch_size, num_workers=48, shuffle=True, prefetch_factor=4)
    valid_dataloader = DataLoader(valid_set, batch_size=args.eval_batch_size, num_workers=48, shuffle=True, prefetch_factor=4)

    no_decay = ["bias", "LayerNorm.weight"]
    optimizer_grouped_parameters = []

    optimizer_grouped_parameters.extend(
        [
            {
                "params": [
                    p
                    for n, p in model.named_parameters()
                    if not any(nd in n for nd in no_decay)
                ],
                "weight_decay": args.weight_decay,
            },
            {
                "params": [
                    p
                    for n, p in model.named_parameters()
                    if any(nd in n for nd in no_decay)
                ],
                "weight_decay": 0.0,
            },
        ]
    )

    optimizer = torch.optim.AdamW(optimizer_grouped_parameters, lr=args.lr)

    model = nn.DataParallel(model)
    global_steps = 0
    etc=0
    for epoch in range(start_epoch, args.epoch):
        model.train()
        triplet_loss=Triplet_COS_Loss(margin=0.2)
        train_iterator = tqdm(train_dataloader)
        loss_list = []
        for i, (seq1,seq2,seq3,mask1,mask2,mask3) in enumerate(train_iterator):
            t1=time.time()
            input_ids1, attention_mask1 = seq1.cuda(),mask1.cuda()
            input_ids2, attention_mask2 = seq2.cuda(),mask2.cuda()
            input_ids3, attention_mask3 = seq3.cuda(),mask3.cuda()

            optimizer.zero_grad()
            anchor,pos,neg=0,0,0

            output1 = model(input_ids=input_ids1, attention_mask=attention_mask1)
            anchor = output1.pooler_output

            output2 = model(input_ids=input_ids2, attention_mask=attention_mask2)
            pos = output2.pooler_output

            output3 = model(input_ids=input_ids3, attention_mask=attention_mask3)
            neg = output3.pooler_output

            optimizer.zero_grad()
            loss = triplet_loss(anchor, pos, neg)

            loss.backward()
            loss_list.append(loss)

            optimizer.step()
            if (i+1) % args.log_every == 0:
                global_steps += 1
                tmp_lr = optimizer.param_groups[0]["lr"]
                # logger.info(f"[*] epoch: [{epoch}/{args.epoch+1}], steps: [{i}/{len(train_iterator)}], lr={tmp_lr}, loss={loss}")
                train_iterator.set_description(f"[*] epoch: [{epoch}/{args.epoch+1}], steps: [{i}/{len(train_iterator)}], lr={tmp_lr}, loss={loss}")
                if WANDB:
                    wandb.log({
                        'triplet loss' : loss,
                        'lr' : tmp_lr,
                        'global_step' : global_steps,
                    })

        if (epoch+1) % args.eval_every == 0:
            logger.info(f"Doing Evaluation ...")
            mrr = finetune_eval(model, valid_dataloader)
            logger.info(f"[*] epoch: [{epoch}/{args.epoch+1}], mrr={mrr}")
            if WANDB:
                wandb.log({
                    'mrr': mrr
                })
            with open(os.path.join(args.output_path, f"finetune_epoch_{epoch+1}_mrr.txt"), 'w') as f:
                f.write(f"{mrr}_{seed}")
        if (epoch+1) % args.save_every == 0:
            logger.info(f"Saving Model ...")
            model.module.save_pretrained(os.path.join(args.output_path, f"finetune_epoch_{epoch+1}"), safe_serialization=False)
            logger.info(f"Done")


def finetune_eval(net, data_loader):
    net.eval()
    with torch.no_grad():
        avg=[]
        gt=[]
        cons=[]
        eval_iterator = tqdm(data_loader)
        for i, (seq1,seq2,_,mask1,mask2,_) in enumerate(eval_iterator):
            input_ids1, attention_mask1= seq1.cuda(),mask1.cuda()
            input_ids2, attention_mask2= seq2.cuda(),mask2.cuda()

            anchor,pos=0,0

            output1 = model(input_ids=input_ids1, attention_mask=attention_mask1)
            anchor = output1.pooler_output

            output2 = model(input_ids=input_ids2, attention_mask=attention_mask2)
            pos = output2.pooler_output

            ans=0
            for i in range(len(anchor)):    # check every vector of (vA,vB)
                vA=anchor[i:i+1].cpu()  #pos[i]
                sim=[]
                for j in range(len(pos)):
                    vB=pos[j:j+1].cpu()   # pos[j]
                    AB_sim=F.cosine_similarity(vA, vB).item()
                    sim.append(AB_sim)
                    if j!=i:
                        cons.append(AB_sim)
                sim=np.array(sim)
                y=np.argsort(-sim)
                posi=0
                for j in range(len(pos)):
                    if y[j]==i:
                        posi=j+1

                gt.append(sim[i])

                ans+=1/posi

            ans=ans/len(anchor)
            avg.append(ans)
        return np.mean(np.array(avg))

class BinBertModel(BertModel):
    def __init__(self, config, add_pooling_layer=True):
        super().__init__(config)
        self.config = config
        self.embeddings.position_embeddings=self.embeddings.word_embeddings

if __name__ == '__main__':
    torch.multiprocessing.set_sharing_strategy('file_system')
    parser = argparse.ArgumentParser(description="jTrans-Finetune")
    parser.add_argument("--model_path", type=str, default='/mnt/hexhive/jtrans/dataset/models/jTrans-pretrain',  help='the path of pretrain model')
    parser.add_argument("--output_path", type=str, default='/mnt/hexhive/jtrans/dataset/models/jTrans-finetune', help='the path where the finetune model be saved')
    parser.add_argument("--tokenizer", type=str, default='./jtrans_tokenizer', help='the path of tokenizer')
    parser.add_argument("--epoch", type=int, default=10, help='number of training epochs')
    parser.add_argument("--lr", type=float, default=1e-5, help='learning rate')
    parser.add_argument("--warmup", type=int, default=1000, help='warmup steps')
    parser.add_argument("--step_size", type=int, default=40000, help='scheduler step size')
    parser.add_argument("--gamma", type=float, default=0.99, help='scheduler gamma')
    parser.add_argument("--batch_size", type=int, default = 64, help='training batch size')
    parser.add_argument("--eval_batch_size", type=int, default = 256, help='evaluation batch size')
    parser.add_argument("--log_every", type=int, default =1, help='logging frequency')
    parser.add_argument("--local_rank", type=int, default = 0, help='local rank used for ddp')
    parser.add_argument("--freeze_cnt", type=int, default=10, help='number of layers to freeze')
    parser.add_argument("--weight_decay", type=int, default = 1e-4, help='regularization weight decay')
    parser.add_argument("--eval_every", type=int, default=1, help="evaluate the model every x epochs")
    parser.add_argument("--eval_every_step", type=int, default=1000, help="evaluate the model every x epochs")
    parser.add_argument("--save_every", type=int, default=1, help="save the model every x epochs")
    parser.add_argument("--train_path", type=str, default='/mnt/hexhive/jtrans/dataset/small_train', help='the path of training data')
    parser.add_argument("--eval_path", type=str, default='/mnt/hexhive/jtrans/dataset/small_test', help='the path of evaluation data')
    parser.add_argument("--load_path", type=str, default='/mnt/hexhive/jtrans/dataset/experiments/BinaryCorp-3M/', help='load path')
    parser.add_argument("--generate", action='store_true', help='generate data')
    parser.add_argument("--opts_path", type=str, help='path to the opts that will be used')
    args = parser.parse_args()

    from datetime import datetime
    now = datetime.now() # current date and time
    TIMESTAMP="%Y%m%d%H%M"
    tim = now.strftime(TIMESTAMP)
    logger = get_logger(f"jTrans_{args.lr}_batchsize_{args.batch_size}_weight_decay_{args.weight_decay}_{tim}")

    logger.info("Loading Tokenizer ...")
    tokenizer = BertTokenizer.from_pretrained(args.tokenizer)
    logger.info("Tokenizer Done ...")


    logger.info("Loading opts ...")
    if args.opts_path != None:
        with open(args.opts_path, 'r') as f:
            opts = json.load(f)
    else:
        opts = ['O0','O1','O2','O3','Os']

    logger.info("Loaded opts")

    # logger.info("Loading Data ...")
    t = time.time()
    if args.generate:
        logger.info("Generating Data ...")
        load_train, load_test = False, False
    else:
        logger.info("Loading Data from pkl ...")
        load_train = f"{args.load_path}/jTrans-{args.train_path.split('/')[-1]}.pkl"
        load_test = f"{args.load_path}/jTrans-{args.eval_path.split('/')[-1]}.pkl"
    
    ft_train_dataset= FunctionDataset_CL_Load(tokenizer,args.train_path,convert_jump_addr=True, load=load_train, opt=opts)
    ft_valid_dataset=FunctionDataset_CL_Load(tokenizer,args.eval_path,convert_jump_addr=True, load=load_test, opt=opts)
    logger.info(f"Done in {time.time() - t} seconds.")
    dump_t = time.time()
    if not load_train:
        pickle.dump(ft_train_dataset.datas, open(f"{args.load_path}/jTrans-{args.train_path.split('/')[-1]}.pkl", 'wb'))
        pickle.dump(ft_valid_dataset.datas, open(f"{args.load_path}/jTrans-{args.eval_path.split('/')[-1]}.pkl", 'wb'))
    logger.info(f"Dumped in {time.time() - dump_t} seconds.")
    logger.info(f"Data Loaded in {time.time() - t} seconds...")
        
    files = glob.glob(os.path.join(args.output_path, 'finetune_epoch_*.txt'))
    if files:
        epoch = max([int(os.path.basename(f).split('_')[-2]) for f in files])
        checkpoint_path = os.path.join(args.output_path, f"finetune_epoch_{epoch}")
        logger.info(f"Loading from checkpoint: {checkpoint_path}")
        model = BinBertModel.from_pretrained(checkpoint_path)
        with open(checkpoint_path + f"_mrr.txt", 'r') as f:
            mrr_stored, seed = f.read().split('_')
            mrr_stored = float(mrr_stored)
            seed = int(seed)
        logger.info(f"[*] epoch: [{epoch}/{args.epoch+1}], mrr_stored={mrr_stored}")
        torch.manual_seed(seed)
        valid_dataloader = DataLoader(ft_valid_dataset, batch_size=args.eval_batch_size, num_workers=48, shuffle=True, prefetch_factor=4)
        mrr_checkpoint = finetune_eval(model, valid_dataloader)
        logger.info(f"[*] epoch: [{epoch}/{args.epoch+1}], mrr_checkpoint={mrr_checkpoint}")
        delta = 0.001
        if abs(mrr_checkpoint - mrr_stored) >= delta:
            logger.info(f"Error: MRR mismatch between checkpoint and stored value. Exiting.")
            sys.exit(1)
        exit(0)

    else:
        epoch = 1 # so we start from 0
        logger.info("No checkpoints found. Starting from scratch.")
        logger.info(f"Loading Pretrained Model from {args.model_path} ...")
        model = BinBertModel.from_pretrained(args.model_path)

        freeze_layer_count = args.freeze_cnt
        for param in model.embeddings.parameters():
            param.requires_grad = False

        if freeze_layer_count != -1:
            for layer in model.encoder.layer[:freeze_layer_count]:
                for param in layer.parameters():
                    param.requires_grad = False 
    print(model)

    logger.info("Done ...")

    # load_train, load_test = False, False
    # load_train = f"{args.load_path}/jTrans-{args.train_path.split('/')[-1]}.pkl"
    # load_test = f"{args.load_path}/jTrans-{args.eval_path.split('/')[-1]}.pkl"
    # ft_train_dataset= FunctionDataset_CL_Load(tokenizer,args.train_path,convert_jump_addr=True, load=load_train, opt=opts)
    # ft_valid_dataset=FunctionDataset_CL_Load(tokenizer,args.eval_path,convert_jump_addr=True, load=load_test, opt=opts)
    # if not load_train:
    #     pickle.dump(ft_train_dataset.datas, open(f"{args.load_path}/jTrans-{args.train_path.split('/')[-1]}.pkl", 'wb'))
    #     pickle.dump(ft_valid_dataset.datas, open(f"{args.load_path}/jTrans-{args.eval_path.split('/')[-1]}.pkl", 'wb'))
    logger.info("Done ...")
    train_dp(epoch - 1, model, args, ft_train_dataset, ft_valid_dataset, logger)
    logger.info("Finished Training")

