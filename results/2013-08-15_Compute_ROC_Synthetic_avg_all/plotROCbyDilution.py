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
    dilutionList = (0.1,0.3,1.0,10.0)

    folderList = ('2013-08-14_Compute_ROC_Synthetic_avg1000','2013-08-14_Compute_ROC_Synthetic_avg10000',)

    
    N=1000 # Z sampling size  
    fig=plt.figure(figsize=(10, 9))
    chi2=False
    if chi2:
        ptitle='ROC_with_chi2'
    else:
        ptitle='ROC_without_chi2'
    plt.suptitle(ptitle)
    for d in dilutionList:
        logging.debug("Processing dilution: %0.1f%%" % d)
        ax = fig.add_subplot(2,2,dilutionList.index(d)+1)
        label=[]
        for f in folderList:            
            controlFile = "../%s/Control.hdf5" %f
            caseFile = "Case%s.hdf5" % str(d).replace(".","_")
            caseFile = "../%(folder)s/%(file)s" %{'folder':f,'file':caseFile}
             # ROC
            
            [fpr,tpr,cov] = ROCpoints(controlFile,caseFile,P=0.95,chi2=chi2)            
            
            ax.plot(fpr,tpr, label='%0.1f' % cov)

        ax.legend(loc=4)
        ax.plot([0,1],[0,1],color='k',linestyle='dashed')
        ax.set_title('%0.1f%% Mutant Mixture' % d)
        ax.set_xlim((-0.01,1.01))
        ax.set_ylim((-0.01,1.01))
                 
        ax.set_xlabel('False Positive Rate')
        ax.set_ylabel('True Positive Rate')
        title = 'dilution%0.1f' % d
        ax.set_title(title.replace('.','_',1))
    plt.savefig(ptitle)

def ROCpoints(controlFile,caseFile,N=1000,P=0.95,chi2=False):
    # Load the model samples
    (controlPhi, controlTheta, controlMu, controlLoc, controlR, controlN) = rvd27.load_model(controlFile)
    
    (casePhi, caseTheta, caseMu, caseLoc, caseR, caseN) = rvd27.load_model(caseFile)

    # Extract the common locations in case and control
    caseLocIdx = [i for i in xrange(len(caseLoc)) if caseLoc[i] in controlLoc]
    controlLocIdx = [i for i in xrange(len(controlLoc)) if controlLoc[i] in caseLoc]
    
    caseMu = caseMu[caseLocIdx,:]
    controlMu = controlMu[controlLocIdx,:]
    caseR = caseR[:,caseLocIdx,:]
    controlR = controlR[:,controlLocIdx,:]
    caseN = caseN[:,caseLocIdx]
    controlN = controlN[:,controlLocIdx]
    
    loc = caseLoc[caseLocIdx]
    J = len(loc)
    pos = np.arange(85,346,20)
    posidx = [i for i in xrange(J) if int(loc[i][8:]) in pos]

    
    # Sample from the posterior Z = muCase - muControl        
    (Z, caseMuS, controlMuS) = rvd27.sample_post_diff(caseMu, controlMu, N)
    
    # Compute cumulative posterior probability for regions (Threshold,np.inf) 
    pList = [rvd27.bayes_test(Z, [(T, np.inf)]) for T in np.linspace(np.min(np.min(Z)), np.max(np.max(Z)), num=300)]
    
    # mutation classification
    clsList = np.array((np.array(pList)>P).astype(int))
    clsList = clsList.reshape((clsList.shape[0],clsList.shape[1]))# category list

    
    # chi2 test for goodness-of-fit to a uniform distribution for non-ref bases
    if chi2:
        nRep = caseR.shape[0]
        chi2Prep = np.zeros((J,nRep))
        chi2P = np.zeros(J)
        for j in xrange(J):
                chi2Prep[j,:] = np.array([rvd27.chi2test( caseR[i,j,:] ) for i in xrange(nRep)] )
                if np.any(np.isnan(chi2Prep[j,:])):
                    chi2P[j] = 0
                else:
                   chi2P[j] = 1-ss.chi2.cdf(-2*np.sum(np.log(chi2Prep[j,:] + np.finfo(float).eps)), 2*nRep) # combine p-values using Fisher's Method
        
        clsList2 = np.array((np.array(chi2P)<0.05/J).astype(int))        
        clsList2 = np.tile(clsList2,(clsList.shape[0],1))
        clsList = np.array(((clsList+clsList2)==2).astype(int))
    
    # false postive rate
    fpr = np.array([float(sum(clsList[i])-sum(clsList[i,np.array(posidx)]))/(clsList.shape[1]-len(posidx)) for i in xrange(clsList.shape[0])])
    
    # true positive rate
    tpr = np.array([float(sum(clsList[i,np.array(posidx)]))/len(posidx) for i in xrange(clsList.shape[0])])

    cov = np.median(caseN)
    return fpr,tpr, cov

if __name__ == '__main__':
    main()

