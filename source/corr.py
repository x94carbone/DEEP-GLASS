#
# Questo e` uno spinoff da bruna10.py. Ecco le modifiche (+ se e` implementata, - se sto per farlo):
# + Vengono letti nuovi parametri relativi ai tempi
# + Vengono generate liste di tempi
# + L'inizializzazione dei pesi viene fatta esplicitamente
# - Viene calcolata la distribuzione dei pesi
# - Viene calcolata la funzione di correlazione
# - Il programma ora puo` correre con qualsiasi delle reti, non solo bruna e bruna10
#
# Note: La loss function viene salvata alla fine del run. Se si
# riprende il run, viene salvata in un file separato, alla fine del
# nuovo run. Questo va bene fintantoche i runs non vengono
# interrotti. Una cosa da fare sarebbe salvarla in un formato
# 'appendable' (testo per esempio), e salvarla a ogni time step, o
# almeno ogni volta che viene salvato il backup .pyT.
#
from __future__ import print_function
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.autograd import Variable
import sys
import argparse
from models.generic_models import loadNet
import numpy as np #for the generation of the time lists

#####################
# Training settings #
#####################
torch.set_default_tensor_type('torch.DoubleTensor')
parser = argparse.ArgumentParser(description='PyTorch Trainer, modified from the MNIST example')
parser.add_argument('--batch-size', type=int, default=64, metavar='B',
                    help='input batch size for training (default: 100)')
parser.add_argument('--load', type=str, default='nil',
                    help='load data and train.')
parser.add_argument('--test-batch-size', type=int, default=1000, metavar='test B',
                    help='input batch size for testing (default: 1000)')
parser.add_argument('--periods', type=int, default=10,
                    help='number of periods to train (default: 10)')
parser.add_argument('--steps_per_period', type=int, default=100, metavar='spp',
                    help='Redefining period (default=100)')
parser.add_argument('--lr', type=str, default='0.01', metavar='LR',
                    help='learning rate (default: 0.01)')
parser.add_argument('--momentum', type=float, default=0.5, metavar='M',
                    help='SGD momentum (default: 0.5)')
parser.add_argument('--no-cuda', action='store_true', default=False,
                    help='disables CUDA training')
parser.add_argument('--seed', type=int, default=1, metavar='S',
                    help='random seed (default: 1)')
parser.add_argument('--print-interval', type=int, default=50,
                    help='how many batches to wait before logging training status')
parser.add_argument('--dataset', type=str, default='cifar10',
                    help='pick one: mnist, cifar10, cifar100')
parser.add_argument('--model', type=str, default='convTest',
                    help='Model to be loaded')
parser.add_argument('--out', type=str, default='./pretrained/',
                    help='Path to be saved (default: ./pretrained/)')
parser.add_argument('--data-size', type=int, default=0,
                    help='Default -1: original dataset size, otherwise dataset is downsampled')
parser.add_argument('--save-every', type=int, default=10,
                    help='1: means saved at every period, 3:means saved every three period. No matter what happens it is saved at the end again.')
#parser.add_argument('--test-freq', type=int, default=0,
#                    help='Default is 0:means that the loss function is measured in a logarithmic succession. If it is not zero, we go back to the usual linear spacing, where -1:means calculated per period 1: means calculate at every batch-step, 3:means test every three step. If test-freq!=0, no matter what happens it is tested at the end again.')
parser.add_argument('--hidden_size', type=int, default=10, metavar='m',
                    help='In some networks we can specify the number of hidden nodes through this option.')
parser.add_argument('--weight_decay', type=float, default=0, metavar='WD',
                    help='Positive: Coefficient of the L2 regularization. Negative: -coefficient of the Bruna-like regularization. Zero: no regularization.')
parser.add_argument('--t0', type=int, default=1, metavar='t0',
                    help='initial t time for C(tw,tw+t) (default: 1)')
parser.add_argument('--tw0', type=int, default=1, metavar='tw0',
                    help='initial tw time for C(tw,tw+t) (default: 1)')
parser.add_argument('--tbar0', type=int, default=1, metavar='tbar0',
                    help='initial t time for Loss(tbar) (default: 1)')
parser.add_argument('--nt', type=int, default=10, metavar='t0',
                    help='number of times t (default: 10)')
parser.add_argument('--ntw', type=int, default=4, metavar='tw0',
                    help='number of times tw (default: 4)')
parser.add_argument('--ntbar', type=int, default=10, metavar='tbar0',
                    help='number of times tbar (default: 10)')


##################
# Cuda and Seeds #
##################
args = parser.parse_args()
print(args)
args.cuda = not args.no_cuda and torch.cuda.is_available()
torch.manual_seed(args.seed)
if args.cuda:
    torch.cuda.manual_seed(args.seed)

#################
# New Arguments #
#################
num_classes=10
#The size of the image is needed
if args.dataset=='cifar100' or args.dataset=='cifar10':
    input_size=3*32*32
elif args.dataset=='mnist':
    input_size=28*28
else:
    print("Wrong args.dataset: ",args.dataset); sys.exit()

############################
# Size of the hidden layer #
############################
hidden_size=args.hidden_size
assert(hidden_size>0)
#Regularization parameters
if args.weight_decay>=0:
    weight_decay=args.weight_decay
    bruna_decay=0
else:
    weight_decay=0
    bruna_decay=-args.weight_decay

############################
# Modified Bruna's Network #
############################
class bruna(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super(bruna, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, num_classes)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        out = self.fc1(x.view(-1,input_size))
        out = self.relu(out)
        out = self.fc2(out)
        out = self.sigmoid(out)
        return out

########################
# Load Bruna's network #
########################
iniPeriod=0
model=bruna(input_size, hidden_size, num_classes)
if args.load != 'nil':
    model=loadNet(args.load,model)
    from re import search
    iniPeriod=1+int(search('_bruna_(.+?).pyT',args.load).group(1))
num_weights=input_size*hidden_size+hidden_size*num_classes+hidden_size+num_classes
inv_num_weights=1.0/num_weights

#################################
# Initialization of the weights #
#################################
def weights_init(m,distr_w='uniform',distr_b='uniform'): #Initializes weights to some distribution
    if distr_w == 'normal':
        m.fc1.weight.data.normal_(0.0, 0.1)
        m.fc2.weight.data.normal_(0.0, 0.1)
    elif distr_w == 'zero':
        m.fc1.weight.data.fill_(0.0)
        m.fc2.weight.data.fill_(0.0)
    elif distr_w == 'ones':
        m.fc1.weight.data.fill_(1.0)
        m.fc2.weight.data.fill_(1.0)
    elif distr_w == 'uniform01':
        m.fc1.weight.data.uniform_(0,1)
        m.fc2.weight.data.uniform_(0,1)
    elif distr_w == 'uniform':
        m.fc1.weight.data.uniform_(-0.02,0.02)
        m.fc2.weight.data.uniform_(-0.02,0.02)
    if distr_b == 'normal':
        m.fc1.bias.data.normal_(0.0, 0.01)
        m.fc2.bias.data.normal_(0.0, 0.01)
    elif distr_b == 'zero':
        m.fc1.bias.data.fill_(0.0)
        m.fc2.bias.data.fill_(0.0)
    elif distr_b == 'ones':
        m.fc1.bias.data.fill_(1.0)
        m.fc2.bias.data.fill_(1.0)
    elif distr_b == 'uniform01':
        m.fc1.bias.data.uniform_(0,1)
        m.fc2.bias.data.uniform_(0,1)
    elif distr_b == 'uniform':
        m.fc1.bias.data.uniform_(-0.02,0.02)
        m.fc2.bias.data.uniform_(-0.02,0.02)
weights_init(model)
    
#########################
# The modified MSE loss #
#########################
def bruna_loss10(output, target):
    this_batch_size=target.numel() #the last batch may be shorter
    temp=output[0].pow(2).sum()+1-2*output[0][target[0].data[0]]    
    for i in range(1,this_batch_size):
        temp+=output[i].pow(2).sum()+1-2*output[i][target[i].data[0]]
    return temp/(this_batch_size*num_classes)
#This is the same as in Bruna's paper
def L1_regularization(mod):
    return torch.norm(mod.fc2.weight,1) + torch.norm(mod.fc2.bias,1)
#In Bruna's paper, they put a bound on the L2 norm of the single row - this is different.
def L2_regularization(mod):
    return torch.norm(mod.fc1.weight,2)+torch.norm(mod.fc1.bias,2)

################################
# Generation of the time lists #
################################
def ListaLogaritmica(x0,xn,n,ints=False,addzero=False):
    assert(xn>x0)
    assert(x0>0)
    n=np.int64(n)
    y0=np.log(x0)
    yn=np.log(xn)
    delta=np.float64(yn-y0)/(n-1)
    listax=np.exp([y0+i*delta for i in range(n)])
    if ints:
        listax=np.unique(np.round(listax,0).astype(int))
    if addzero:
        listax=np.insert(listax,0,0)
    return listax

#Parameters that are not argparsed
total_time=np.int64(args.steps_per_period*args.periods) #Total number of batches, which is our time unit
tbarn=total_time
tn=np.int64(0.5*total_time);
twn=np.int64(0.5*total_time);

listatw=ListaLogaritmica(args.tw0,twn,args.ntw,ints=True,addzero=True)
listat=ListaLogaritmica(args.t0,tn,args.nt,ints=True,addzero=True)
listatbar=set(ListaLogaritmica(args.tbar0,tbarn,args.ntbar,ints=True,addzero=True))
#The list of the tprimes is a little harder
listatprime=[]; which_itwit=[]; howmany_tprime=[]
itprime=0
for itw in range(len(listatw)):
    for it in range(len(listat)):
        value=listat[it]+listatw[itw]
        if value in listatprime:
            itprime_old=listatprime.index(value)
            which_itwit[itprime_old].append([itw,it])
            howmany_tprime[itprime_old]+=1
        else:
            listatprime.append(value)
            which_itwit.append([[itw,it]])
            howmany_tprime.append(1)
            itprime+=1
listatprime=listatprime
print("listatw = ",listatw)
print("listat = ",listat)
print("listatbar = ",listatbar)
print("listatprime = ",listatprime)

#####################
# Extra Observables #
#####################
#Histogram of the weights
nbins=20
histw_evol_x=torch.Tensor(args.ntw+1,nbins+1) #Histogram of all weights. The +1 is because I include time zero.
histw_evol_y=torch.Tensor(args.ntw+1,nbins)
#1-time quantities
#Weights at time tw
w_evol=torch.Tensor(args.ntw+1,num_weights)
wtilde_evol=torch.Tensor(args.ntw+1,num_weights)
#2-time quantities
#Correlation function
corrw=torch.Tensor(args.ntw+1,args.nt+1)      #Correlation of the weights
corrwtilde=torch.Tensor(args.ntw+1,args.nt+1) #Correlation of the rescaled weights



################
# Data Loading #
################
kwargs = {'num_workers': 1, 'pin_memory': True} if args.cuda else {}
from train_utils import getDataset,cycle_loader

train_loader = getDataset(args.dataset,sample_size=args.data_size,b_size=args.batch_size,**kwargs)
circ_train_loader = cycle_loader(train_loader)
test_loader = getDataset(args.dataset,train=False,b_size=args.test_batch_size,**kwargs)

if args.cuda:
    model.cuda()

args.lr = float(args.lr)

def updateOptimizer(old,fun,model,period,batch_idx,*f_args):
    new_lr = fun(model,*f_args)
    if new_lr and 0<new_lr<1:
        loss_hist['lr'].append((period,batch_idx,new_lr))
        old = optim.SGD(model.parameters(), lr=new_lr, momentum=args.momentum, weight_decay=weight_decay)
    return old

loss_hist = {'train':[],'test':[],'lr':[]} ##losses before steps
def logPerformance(model,period,batch_idx):
    loss_tuple = test(period,test_loader,print_c=True)
    loss_hist['test'].append((period,batch_idx,loss_tuple))
    loss_tuple = test(period,train_loader,print_c=True,label='Train')
    loss_hist['train'].append((period,batch_idx,loss_tuple))

def getWeights(model):
    paramlist=list(model.parameters())
    pesi1=paramlist[0].data.view(paramlist[0].data.numel())
    bias1=paramlist[1].data.view(paramlist[1].data.numel())
    pesi2=paramlist[2].data.view(paramlist[2].data.numel())
    bias2=paramlist[3].data.view(paramlist[3].data.numel())
    return torch.cat((pesi1,bias1,pesi2,bias2),0)

def train(period,n_step = 1000,lr=args.lr):
    model.train()
    optimizer=optim.SGD(model.parameters(), lr=lr, momentum=args.momentum, weight_decay=weight_decay)
    for batch_idx, (data, target) in enumerate(circ_train_loader):
        if args.cuda:
            data, target = data.cuda(), target.cuda()
        data, target = Variable(data), Variable(target)
        optimizer.zero_grad()
        output = model(data)
        loss = bruna_loss10(output, target)
        if bruna_decay>0:#This is because bruna_decay is often chosen to be zero
            loss+=bruna_decay*(L1_regularization(model)+L2_regularization(model))
        loss.backward()

        absolute_batch_idx=batch_idx+(period-1)*n_step #The -1 is because periods start from 1
        if absolute_batch_idx in listatbar: #Loss function and accuracy
            logPerformance(model,period,batch_idx)

        if absolute_batch_idx in listatw: #Save states w and measure p(w)
            itw=np.where(listatw==absolute_batch_idx)[0][0]
            w=getWeights(model)
            w_evol[itw]=w.clone() #We need this for C(tw,t'=t+tw)
            wtilde_evol[itw]=w*num_weights/w.abs().sum() #We need this for C(tw,t'=t+tw)
            histw=np.histogram(w.numpy(),bins=nbins,normed=False,weights=None)
            histw_evol_x[itw]=torch.from_numpy(np.array(histw[1]))
            histw_evol_y[itw]=torch.from_numpy(np.array(histw[0]))

        if absolute_batch_idx in listatprime: #Measure correlation functions
            itprime=list(listatprime).index(absolute_batch_idx)
            w=getWeights(model)
            wtilde=w*num_weights/w.abs().sum()
            for icomb in range(howmany_tprime[itprime]):
                [itw,it]=which_itwit[itprime][icomb]
                assert(listatw[itw]+listat[it]==absolute_batch_idx)
                square_corrw=torch.pow(w-w_evol[itw],2).sum()
                square_corrwtilde=torch.pow(wtilde-wtilde_evol[itw],2).sum()
                corrw[itw][it]=inv_num_weights*square_corrw
                corrwtilde[itw][it]=inv_num_weights*square_corrwtilde
                assert(square_corrw>=0)
                assert(square_corrwtilde>=0)

        optimizer.step()
        if batch_idx % args.print_interval == 0:
            print('Train Period: {} [{}/{} ({:.0f}%)]\tLoss: {: .6f}'.format(
                period, batch_idx * len(data), n_step * len(data),
                100. * batch_idx / n_step, loss.data[0])) 
        if batch_idx==n_step:
            break

def test(period,data_loader,print_c=False,label='Test'):
    model.eval()
    test_loss = 0
    correct = 0
    for data, target in data_loader:
        if args.cuda:
            data, target = data.cuda(), target.cuda()
        data, target = Variable(data, volatile=True), Variable(target)
        output = model(data)
        test_loss += (bruna_loss10(output, target)+bruna_decay*(L1_regularization(model)+L2_regularization(model))).data[0]
        pred = output.data.max(1)[1] # get the index of the max log-probability
        correct += pred.eq(target.data).cpu().sum()

    test_loss = test_loss
    test_loss /= len(data_loader) # loss function already averages over batch size
    if print_c: print('\n{} set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(label,
        test_loss, correct, len(data_loader.dataset),
        100. * correct / len(data_loader.dataset)))
    return (test_loss, correct, len(data_loader.dataset))




######################
# Output information #
######################
base_path = args.out+'_'.join([args.dataset,str(args.data_size),str(args.batch_size),args.model])
save_at = set(range(0,args.periods+1,max(1,args.save_every)))
save_at.add(args.periods)
if args.data_size != 0:
    torch.save(list(train_loader.dataset),base_path+'.data')


#####################
# Train the network #
#####################
for period in range(iniPeriod, args.periods + 1):
    if period != 0: #So that initial state is saved
        train(period,n_step=args.steps_per_period)
    if period in save_at:
        out = model.state_dict()
        for k,v in out.items():
            out[k]=v.cpu()
        torch.save(out,base_path+'_%05d.pyT'%period)
torch.save(args,base_path+'.args')
torch.save(loss_hist,base_path+"_{0}-{1}.hist".format("%05d"%iniPeriod,"%05d"%period))




###################
#Some more saving #
###################
#Save P(w)
histfile=file(args.out+args.dataset+'_histw.txt','a')
for itw in range(len(listatw)):
    delta=histw_evol_x[itw][1]-histw_evol_x[itw][0]
    xcenters=histw_evol_x[itw][0:nbins].numpy()+0.5*delta
    ycenters=histw_evol_y[itw].numpy()
    normalized_ycenters=ycenters/(num_weights*delta)
    # plt.plot(xcenters, normalized_ycenters, linewidth='3.0', label='t='+str(listatw[itw]))
    header='1)itw 2)tw 3)w 4)h(w) 5)p(w)' if itw==0 else ''
    np.savetxt(histfile, np.stack(([itw for i in range(len(xcenters))],[listatw[itw] for i in range(len(xcenters))],xcenters,ycenters,normalized_ycenters),axis=1), fmt='%.14g', delimiter=' ', newline='\n', header=header, footer='', comments='# ')
# plt.legend(loc='lower center')
# plt.show()
histfile.close()
#save C(tw,t')
f1=open(args.out+args.dataset+'_C.txt', 'w+')
f1.write('#1)itw 2)it 3)tw 4)t 5)C(tw,tw+t) 6)Ctilde(tw,tw+t)\n')
f1.write('#Time is measured in batches, so it should be multiplied by the batch size\n')
for itprime in range(len(listatprime)):
    for icomb in range(howmany_tprime[itprime]):
        [itw,it]=which_itwit[itprime][icomb]
        f1.write(str(itw)+' '+str(it)+' '+str(listatw[itw])+' '+str(listat[it])+' '+str(corrw[itw][it])+' '+str(corrwtilde[itw][it])+'\n')
f1.close()
