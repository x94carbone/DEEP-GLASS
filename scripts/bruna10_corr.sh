#!/bin/bash
# Script to launch bruna network
# 
set -x


export PYTHONPATH=$PYTHONPATH:/home/mbaityje/miniconda2/pkgs/pytorch-0.2.0-py27h44c09ab_2cu75/lib/python2.7/site-packages/:
export PATH=/home/mbaityje/miniconda2/bin:$PATH

#--SYSTEM RECOGNITION--
#SYSTEM="kondo"
SYSTEM="PennPuter"
if [ $SYSTEM == "kondo" ];then 
    if ! [[ `hostname` == *"kondo"* ]];then #the string "kondo" must be contained in hostname
	echo "ATTENZIONE: System declared as $SYSTEM, but it actually is $(hostname)"
    fi
    readonly QUEUE="glass" 
fi
if [ $SYSTEM == "PennPuter" ];then 
    if ! [ `hostname` == "PennPuter" ];then
	echo "ATTENZIONE: System declared as $SYSTEM, but it actually is $(hostname)"
    fi
fi

#--DATASET--
readonly dataset='cifar10'

#--DIRECTORIES--
scriptDIR=$PWD/
myROOT=$PWD/../
exeDIR=$myROOT/source
outROOT=$myROOT/output #Parent directory for all the output
dataDIR=$myROOT/data_$dataset
logDIR=$myROOT/logs

#--NETWORK--
model='bruna10'
prog=corr.py

#--HYPERPARAMETERS--
LEARNING_RATES="0.1" #"0.005 0.01 0.1 0.2"
HIDDEN_SIZES="10" #"30 100 300 1000 3000 10000 30000"
WEIGHT_DECAYS="0" #Positive: L2, Negative: Bruna, Zero: None
BATCH_SIZES="100" #"10 100"
MOMENTA="0.5" #"0 0.5"
SAMPLES="0"

#Length of simulation
TOTLENGTH_NORM=100000 #`echo 10^6|bc` #This is the relevant time, LR*TOTLENGTH, which we want equal for all LR
USE_BACKUPS="no"



#--CYCLE OVER PARAMETERS--
cd $myROOT
for LR in $LEARNING_RATES
do
    #Length of simulation (keep these quantities multiples (or better powers) of 10)
    TOTLENGTH=`echo $TOTLENGTH_NORM/$LR|bc` #Total number of processed images
    periods=1000     # number of periods
    save_every=`echo $periods/4|bc`  # we save 4 times during the run

    for BS in $BATCH_SIZES
    do
	spp=`echo "$TOTLENGTH/($BS*$periods)"|bc`
	if [ $spp -lt 1 ];then echo "spp=$spp is not positive"; exit; fi
	
	for HS in $HIDDEN_SIZES
	do
	    for WD in $WEIGHT_DECAYS
	    do
		for MOMENTUM in $MOMENTA
		do
		    for ISAM in $SAMPLES
		    do
			echo "$model LR=$LR, BS=$BS, m=$HS, WD=$WD, ISAM=$ISAM"
			
			#--Output directory--
			outDIR=$outROOT/${model}corr/m$HS/B${BS}/LR$LR/WD$WD/MOM$MOMENTUM/sam$ISAM/
			mkdir -p $outDIR
			
			#--Backups--
			if [ $USE_BACKUPS == "yes" ]; then
			    lastSave=`ls -rt $dataDIR/*.pyT|tail -1`
			    echo "LAST SAVE: $lastSave"
			    startFrom=${lastSave:-'nil'}
			elif [ $USE_BACKUPS == "no" ]; then
			    startFrom='nil' #I never want to start from the backup
			else
			    echo "USE_BACKUPS = $USE_BACKUPS   not recognized"
			    exit
			fi

			#It's crappy but it does for our purpose
			SEED=`od -vAn -N4 -tu4 < /dev/urandom | sed 's/[[:space:]]//g'`
			
			#--Launch in interactive (PennPuter) or via queues (kondo)
			if [ $SYSTEM == "PennPuter" ]
			then
	    		    echo "python $exeDIR/$prog $exeDIR/$prog --dataset=$dataset --seed=$SEED --steps_per_period=$spp --periods=$periods --batch-size=$BS --test-batch-size=$BS --hidden_size=$HS --out=$outDIR --save-every=$save_every --lr=$LR --model=$model --weight_decay=$WD --load=$startFrom --momentum=$MOMENTUM"
			    time (python $exeDIR/$prog --dataset=$dataset --seed=$SEED --steps_per_period=$spp --periods=$periods --batch-size=$BS --test-batch-size=$BS --hidden_size=$HS --out=$outDIR --save-every=$save_every --lr=$LR --model=$model --weight_decay=$WD --load=$startFrom --momentum=$MOMENTUM) 2>&1
			elif [ $SYSTEM == "kondo" ]
			then
			    nombre=${model}m${HS}lr${LR}bs${BS}s${ISAM}
			    echo "Process name: $nombre"
			    echo "qsub -N $nombre -v dataset=$dataset,SEED=$SEED,spp=$spp,periods=$periods,BS=$BS,HS=$HS,outDIR=$outDIR,save_every=$save_every,LR=$LR,model=$model,WD=$WD,startFrom=$startFrom -j oe -o $logDIR/$nombre.$$.txt bruna10.qsub"
			    echo "Mettere MOMENTUM e SEED nel .qsub"
			    exit
			    qsub -N $nombre -q $QUEUE -v dataset=$dataset,SEED=$SEED,spp=$spp,periods=$periods,BS=$BS,HS=$HS,outDIR=$outDIR,save_every=$save_every,LR=$LR,model=$model,WD=$WD,MOMENTUM=$MOMENTUM,startFrom=$startFrom -j oe -o $logDIR/$nombre.$$.txt $scriptDIR/bruna10.qsub
			fi
			
		    done
		done
	    done
	done
    done
done
cd $scriptDIR