import pickle
import sys
from datautils.playdata import DatasetBase as DatasetBase
from torch.utils.data import DataLoader
import torch
import torch.nn.functional as F
import numpy as np
from tqdm import tqdm
import argparse
import json
import os

def eval_O(ebds,TYPE1,TYPE2, log_file=None):
    funcarr1=[]
    funcarr2=[]

    for i in range(len(ebds)):
        if ebds[i].get(TYPE1) is not None and type(ebds[i][TYPE1]) is not int:
                ebd1=ebds[i][TYPE1]
                funcarr1.append(ebd1 / ebd1.norm())
        else:
            continue
    
    for i in range(len(ebds)):
        if ebds[i].get(TYPE2) is not None and type(ebds[i][TYPE2]) is not int:
                ebd2=ebds[i][TYPE2]
                funcarr2.append(ebd2 / ebd2.norm())
        else:
            continue
    # print(len(funcarr1), len(funcarr2))
    ft_valid_dataset=FunctionDataset_Fast(funcarr1,funcarr2)
    dataloader = DataLoader(ft_valid_dataset, batch_size=min(len(funcarr1), len(funcarr2)), num_workers=0, shuffle=True)
    # print(len(dataloader))
    SIMS=[]
    Recall_AT_1=[]
    matches = []
    mismatches = []
    b_sims = []

    # for idx, (anchor,pos) in enumerate(dataloader):
    anchor = torch.stack(funcarr1).squeeze().cuda()
    pos = torch.stack(funcarr2).squeeze().cuda()
    # print(anchor.shape)
    pos =pos.cuda()
    # print(pos.shape)
    # print(anchor, pos)
    # print(anchor.shape)
    # if anchor.shape[0]==POOLSIZE:
    for i in range(len(anchor)):    # check every vector of (vA,vB)
        vA=anchor[i:i+1]  #pos[i]
        sim = np.array(torch.mm(vA, pos.T).cpu().squeeze())
        # print(anchor.shape, pos.shape, sim.shape)
        y=np.argsort(-sim)
        # print(sim)
        # print(y[0])
        posi=0
        b_sims.append(sim[y[0]])
        tqdm.write(f"{TYPE1} {TYPE2} {ebds[i].get('funcname')} {ebds[y[0]].get('funcname')} {sim[y[0]]}\n")
        if log_file != None:
            log_file.write(f"{TYPE1} {TYPE2} {ebds[i].get('funcname')} {ebds[y[0]].get('funcname')} {sim[y[0]]}\n")
        # if np.isnan(sim[y[0]]):
        #     print(sorted(sim))
        #     exit(1) 
            # for j in range(len(pos)):
            #     if y[j]==i:
            #         posi=j+1
            #         break 
            # if posi==1:
            #     Recall_AT_1.append(1)
            #     matches.append([ebds[i].get('funcname'), ebds[y[0]].get('funcname')])
            # else:
            #     # print(ebds[i].get('funcname'), ebds[y[0]].get('funcname'))
            #     # if log_file != None:
            #     #     log_file.write(f"{ebds[i].get('funcname')} {ebds[y[0]].get('funcname')}")
            #     # matches.append([ebds[i].get('funcname'), ebds[y[0]].get('funcname')])
            #     mismatches.append([ebds[i].get('funcname'), ebds[y[0]].get('funcname')])
            #     Recall_AT_1.append(0)
            # SIMS.append(1.0/posi)
            # print(ebds[i].get('funcname'), ebds[y[0]].get('funcname'))
            # if log_file != None:
            #     log_file.write(f"{ebds[i].get('funcname')} {ebds[y[0]].get('funcname')}\n")
    # print(np.array(b_sims).mean(), b_sims)
    # if np.isnan(np.array(b_sims).mean()):
    #     print(b_sims)
    #     exit(1)
    # sims_r = np.array(SIMS).mean()
    # recall_r = np.array(Recall_AT_1).mean()
    # tqdm.write(f"{TYPE1} {TYPE2}\n")
    # tqdm.write(f"{TYPE1} {TYPE2} Recall@1: {recall_r}\n")
    # for m in matches:
    #     tqdm.write(f"{m[0]} {m[1]}\n")
    # for m in mismatches:
    #     tqdm.write(f"{m[0]} {m[1]}\n")    
    
    # if log_file != None:
    #     log_file.write(f"{TYPE1} {TYPE2} MRR{POOLSIZE}: {sims_r}\n")
    #     log_file.write(f"{TYPE1} {TYPE2} Recall@1: {recall_r}\n")
    #     log_file.write(f"{TYPE1} {TYPE2} Matches\n")
    #     for m in matches:
    #         log_file.write(f"{m[0]} {m[1]}\n")
    #     log_file.write(f"{TYPE1} {TYPE2} Mismatches\n")
    #     for m in mismatches:
    #         log_file.write(f"{m[0]} {m[1]}\n")
    return np.array(b_sims).mean()

class FunctionDataset_Fast(torch.utils.data.Dataset): 
    def __init__(self,arr1,arr2): 
        self.arr1=arr1
        self.arr2=arr2
        # assert(len(arr1)==len(arr2))
    def __getitem__(self, idx):            
        return self.arr1[idx].squeeze(0),self.arr2[idx].squeeze(0)
    def __len__(self):
        return len(self.arr1)

def print_info(title, op1, res, f):
    print(f"{title} results for {op1} is {res[0]} with mrr of {res[1]} and recall@1 of {res[2]} and sim of {res[3]}")
    if f != None:
        f.write(f"{title} results for {op1} is {res[0]} with mrr of {res[1]} and recall@1 of {res[2]} and sim of {res[3]}\n")
def print_best_worst(title, op1, res, f):
    print_info("Best " + title, op1, res[0], f)
    print_info("Worst " + title, op1, res[-1], f)
    if f != None:
        f.write("\n")
        
def flatten(xss):
    return [x for xs in xss for x in xs]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="jTrans-FastEval")
    parser.add_argument("--experiment_path", type=str, default='./jTrans.pkl', help="experiment to be evaluated")
    parser.add_argument("--poolsize", type=int, default=32, help="size of the function pool")
    parser.add_argument("--opts_path", type=str, help='path to the opts that will be used')
    parser.add_argument("--log_path", type=str, default='./', help='path to the directory containing the log file')
    args = parser.parse_args()

    print("Loading opts ...")
    if args.opts_path != None:
        with open(args.opts_path, 'r') as f:
            opts = json.load(f)
    else:
        opts = ['O0','O1','O2','O3','Os']

    print("Loaded opts")

    print("Starting")
    POOLSIZE=args.poolsize
    ff = open(args.experiment_path,'rb')
    ebds=pickle.load(ff)
    ff.close()

    print(f'evaluating...poolsize={POOLSIZE}')
    
    from datetime import datetime
    now = datetime.now() # current date and time
    TIMESTAMP="%Y%m%d%H%M"
    tim = now.strftime(TIMESTAMP)
    f = open(os.path.join(args.log_path, f"eval_{args.experiment_path.replace('/', '_')}_{tim}.txt"), "w")
    
    results = {}
    for op1 in tqdm(opts):
        # if op1 == "ce70847fa23d664c418542c3d40285da63bf00df41b556f20d2dd2179dfe0120":
        results[op1] = []
        for op2 in opts:
            # if op1 == op2:
            # #     # results[op1].append([op2, np.nan, np.nan])
            #     continue
            # else:
                sim = eval_O(ebds, op1, op2, f)
                results[op1].append([op2, sim])
    for op1 in opts:
        v = sorted(results[op1], key=lambda x: x[1])[::-1]
        for a in v:
            print("Sims", op1, a[0], a[1])
            f.write(f"Sims {op1} {a[0]} {a[1]}\n")
    # print("------------------------------------")
    # if f != None:
    #     f.write("------------------------------------\n")
    # mrr = []
    # recall = []
    # for op1 in opts:
    #     # if op1 == "ce70847fa23d664c418542c3d40285da63bf00df41b556f20d2dd2179dfe0120":
    #     vals_mrr = []
    #     sorted_mrr = sorted(results[op1], key = lambda x:x[1])
    #     best_mrr_val = sorted_mrr[-1][1]
    #     worst_mrr_val = sorted_mrr[0][1]

    #     vals_recall = []
    #     sorted_recall = sorted(results[op1], key = lambda x:x[2])
    #     best_recall_val = sorted_recall[-1][2]
    #     worst_recall_val = sorted_recall[0][2]

    #     vals_sims = []
    #     sorted_sims = sorted(results[op1], key = lambda x:x[3])
    #     best_sims_val = sorted_sims[-1][2]
    #     worst_sims_val = sorted_sims[0][2]
    #     for b in sorted_mrr[::-1]:
    #         if b[1] < best_mrr_val:
    #             break
    #         print_info("Best mrr", op1, b, f)
    #         vals_mrr.append([op1, b])

    #     print("------------------------------------")
    #     if f != None:
    #         f.write("------------------------------------\n")

    #     for b in sorted_recall[::-1]:
    #         if b[2] < best_recall_val:
    #             break
    #         print_info("Best recall", op1, b, f)
    #         vals_recall.append([op1, b])

    #     for b in sorted_sims[::-1]:
    #         # if b[3] < best_recall_val:
    #         #     break
    #         print_info("Sims", op1, b, f)
    #         vals_recall.append([op1, b])
    #     print("------------------------------------")
    #     if f != None:
    #         f.write("------------------------------------\n")

    #     for b in sorted_mrr:
    #         if b[1] > worst_mrr_val:
    #             break
    #         print_info("Worst mrr", op1, b, f)
    #         vals_mrr.append([op1, b])

    #     print("------------------------------------")
    #     if f != None:
    #         f.write("------------------------------------\n")

    #     for b in sorted_recall:
    #         if b[2] > worst_recall_val:
    #             break
    #         print_info("Worst recall", op1, b, f)
    #         vals_recall.append([op1, b])
        
    #     print("------------------------------------")
    #     if f != None:
    #         f.write("------------------------------------\n")

    #     mrr.append(vals_mrr)
    #     recall.append(vals_recall)


        

    #     best_mrr_val = max((x[1] for outer in mrr for inner in outer for x in inner[1:]))
    #     best_mrr = [(inner[0], x) for outer in mrr for inner in outer for x in inner[1:] if x[1] == best_mrr_val]
        
    #     best_recall_val = max((x[2] for outer in recall for inner in outer for x in inner[1:]))
    #     best_recall = [(inner[0], x) for outer in recall for inner in outer for x in inner[1:] if x[2] == best_recall_val]
    
    #     worst_mrr_val = min((x[1] for outer in mrr for inner in outer for x in inner[1:]))
    #     worst_mrr = [(inner[0], x) for outer in mrr for inner in outer for x in inner[1:] if x[1] == worst_mrr_val]

    #     worst_recall_val = min((x[2] for outer in recall for inner in outer for x in inner[1:]))
    #     worst_recall = [(inner[0], x) for outer in recall for inner in outer for x in inner[1:] if x[2] == worst_recall_val]

    # for b in best_mrr:
    #     print_info("Overall best mrr", b[0], b[1], f)
    #     print(b[1][3])

    # print("------------------------------------")
    # if f != None:
    #     f.write("------------------------------------\n")

    # for b in best_recall:
    #     print_info("Overall best recall", b[0], b[1], f)
    #     print(b[1][3])

    # print("------------------------------------")
    # if f != None:
    #     f.write("------------------------------------\n")

    # for w in worst_mrr:
    #     print_info("Overall worst mrr", w[0], w[1], f)
    #     print(w[1][3])

    # print("------------------------------------")
    # if f != None:
    #     f.write("------------------------------------\n")

    # for w in worst_recall:
    #     print_info("Overall worst recall", w[0], w[1], f)
    #     print(w[1][3])

    if f != None:
        f.close()