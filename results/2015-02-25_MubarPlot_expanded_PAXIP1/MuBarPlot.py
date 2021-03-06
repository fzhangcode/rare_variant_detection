import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import h5py
import logging
import pdb
import scipy.stats as ss

# Insert the src/python/rvd27 directory at front of the path
rvddir = os.path.join('../../src/python/rvd27')
sys.path.insert(0, rvddir)
import rvd27

logging.basicConfig(level=logging.DEBUG,
                    format='%(levelname)s:%(message)s')

def main():

    #controlFile = '../2013-12-20_experiment_set_gibbs_Qsd_mu_1_mu_over_10_minus_mu0/HCC1187_PAXIP1_genome/Control.hdf5'
    #caseFile = '../2013-12-20_experiment_set_gibbs_Qsd_mu_1_mu_over_10_minus_mu0/HCC1187_PAXIP1_genome/Case.hdf5'
    controlFile = '../2015-02-11_Expand_region_of_interest_of_PAXIP1_gene/control_HCC1187BL.hdf5'
    caseFile = '../2015-02-11_Expand_region_of_interest_of_PAXIP1_gene/case_HCC1187C.hdf5'
    
    hdf5name = 'HCC1187_call.hdf5'


    try:
        with h5py.File(hdf5name, 'r') as f:
                somatic_call = f['somatic_call'][...]
                germline_call = f['germline_call'][...]
    
                controlMu = f['controlMu'][...]
                caseMu = f['caseMu'][...]
                loc = f['loc'][...]
                f.close()


    except IOError as e:       
        germline_alpha = 0.05
        somatic_alpha = 0.05
        diff_tau = 0.0
        N = 1000

        germ_roi = [0.05, np.inf]
        som_roi = [0.0, np.inf]

        hdf5name = 'germlineccall.hdf5'
        try:
            with h5py.File(hdf5name, 'r') as f:
                    germline_call = f['call'][...]
        
                    controlMu = f['controlMu'][...]
                    caseMu = f['caseMu'][...]
                    loc = f['loc'][...]
                    f.close()

        except IOError as e:
            # [loc, germline_call, controlMu, caseMu, controlN, caseN] = rvd27.germline_test(controlFile, caseFile, germline_roi=roi, outputFile='germlinecalltable.vcf')
            #[loc, germline_call, controlMu, caseMu, controlN, caseN] = rvd27.germline_test(germline_alpha, controlFile, caseFile, germline_roi=roi, outputFile='germlinecalltable.vcf')
            [germline_call, loc, controlMu] = rvd27.germline_test(controlFile, intvl=germ_roi, alpha=germline_alpha, outputFile='germlinecalltable.vcf')

        hdf5name = 'somaticcall.hdf5'
        try:
            with h5py.File(hdf5name, 'r') as f:
                    somatic_call = f['call'][...]
                    f.close()

        except IOError as e:
            #[_, somatic_call, _,_,_,_] = rvd27.somatic_test(somatic_alpha, controlFile, caseFile, diff_tau=diff_tau, somatic_roi=roi, N=N,  outputFile='somaticcalltable.vcf')
            [somatic_call, loc, controlMu, caseMu] = rvd27.somatic_test(controlFile, caseFile, intvl=som_roi, alpha=somatic_alpha, N=N, outputFile='somaticcalltable.vcf')

        
        hdf5name = 'HCC1187_call.hdf5'
        with h5py.File(hdf5name, 'w') as f:
                f.create_dataset('somatic_call', data=somatic_call)
                f.create_dataset('germline_call', data=germline_call)
                f.create_dataset('caseMu',data=caseMu)
                f.create_dataset('controlMu',data=controlMu)
                f.create_dataset('loc',data=loc)
                f.close()
    
    call = [somatic_call,germline_call]
    call = np.sum(call,0) > 0  
    
 
    MuBarPlot(controlMu[call], caseMu[call], loc[call],'HCC1187_MuBarPlot.pdf')
    

def MuBarPlot(CallControlMu,CallCaseMu,Loc,title):
    # 95% credible interval
    alpha = 0.05

    pos = int(CallControlMu.shape[1]*alpha/2)

    # sort along Gibbs samples
    ControlMu = np.sort(CallControlMu,axis=1)
    Control_yerr = np.array([np.mean(CallControlMu,1)-ControlMu[:,pos], ControlMu[:,CallControlMu.shape[1]-pos]-np.mean(CallControlMu,1)])

    CaseMu = np.sort(CallCaseMu,axis=1)
    Case_yerr = np.array([np.mean(CallCaseMu,1)-CaseMu[:,pos], CaseMu[:,CallCaseMu.shape[1]-pos]-np.mean(CallCaseMu,1)])
    
    if len(Loc) is not 0:
        ind = np.arange(CallCaseMu.shape[0])
        width=0.35
        fig, ax = plt.subplots(figsize=(16,6))

        rects1 = ax.bar(ind, np.mean(CallControlMu,1), width, color='0.8', yerr=Control_yerr,ecolor='k')
        rects2 = ax.bar(ind+width, np.mean(CallCaseMu,1), width, color='0.5', yerr=Case_yerr,ecolor='k')
        #ax.set_xlim([0, 12])
        ax.set_xlim([-0.2, 15])
            
        ax.set_ylabel('Estimate Minor Allele Frequency')
        ax.set_xlabel("HG19 Genomic Location [chr7:154,700,000+X]")
        ax.set_xticks(ind+width)
        
        #somaticcall = [1,2,3,4,5,7,8,9]
        somaticcall = [1,2,3,4,5,6,7,8,13,14]
        print somaticcall
        
        for i in somaticcall:
            ax.text(i+width-width/5.0, 1.015 ,'*',color='r',fontsize=15)

        #germlinecall = [0, 1, 2, 3, 4, 6, 10, 11]
        germlinecall = [0, 1, 2, 3, 4, 9, 10, 11, 12,13,14]
        print germlinecall
        
        for i in germlinecall:
            ax.text(i+width-width/4.0, 1.0015,r'$\diamond$',color = 'b', fontsize=13)

        
        Loclabel = [x.split(':')[1][4:] for x in Loc]
        
        #rslabel = ['rs1239326', ' ' ,'rs1239324', '  rs71534174' ,'     rs35505514', ' ' , ' ' , ' ' , ' ' , ' ' ,'rs4398858', ' ']
        rslabel = ['rs1239326', ' ' ,'rs1239324', '  rs71534174' ,'     rs35505514', ' ' , ' ' , ' ' , ' ' ,'rs4398858', 'rs10276898','rs306280','rs306279','rs62471878', 'rs306278'] 
    
        label = ['%s\n%s' %(Loclabel[i], rslabel[i]) for i in xrange(len(Loclabel))]

        ax.set_xticklabels(label)
        
        fsize=11

        lgd = ax.legend( (rects1[0], rects2[0]), ('Control', 'Case'), bbox_to_anchor=(0.85, 1.05, 0.15, .102),
                   loc=4,ncol=1, mode="expand", borderaxespad=0., prop={'size':fsize})

        plt.rcParams.update({'font.size': fsize, 'font.family': 'serif'})
        fig.tight_layout(rect=[0, 0, 0.95, 0.9])

        plt.savefig(title, bbox = 'tight', bbox_extra_artists=(lgd,))
        
    else:
        print 'No variant is called'

if __name__ == '__main__':
    main()
