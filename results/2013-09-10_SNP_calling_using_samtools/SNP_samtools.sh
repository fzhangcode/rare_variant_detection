#!/bin/sh
BAMDIR=../../data/Synthetic_BAM_files
BAMFILE=$BAMDIR/*.bam

PICARD=/usr/local/pjf/picard-tools-1.96
FASTAFILE=../../data/Synthetic_BAM_files/plasmid.fa
VCFUTILS=/home/pjflaherty/flahertylab/apps/samtools/bcftools/vcfutils.pl

DRATELIST=(0.1 0.01 0.001 0.0001)
J=(0 1 2 3)
MAXDEPTH=100000

for j in ${J[@]:0:4}
do
	DRATE=${DRATELIST[$j]}
	DFRAC=$(echo $DRATE $MAXDEPTH | awk '{printf "%2.0f\n",$1*$2}')

	echo -------------------------------------------------------------

	DOWNDIR=../2013-08-06_Downsample_Read_Depth/bam/$DFRAC

	SORTBAM0_1=$(ls $DOWNDIR/20100916_c1_p?.07*.sorted.bam  $DOWNDIR/20100916_c1_p?.12*.sorted.bam $DOWNDIR/20100916_c1_p?.14*.sorted.bam)
	SORTBAM0_3=$(ls $DOWNDIR/20100916_c2_p?.02*.sorted.bam  $DOWNDIR/20100916_c2_p?.04*.sorted.bam $DOWNDIR/20100916_c2_p?.05*.sorted.bam)
	SORTBAM1_0=$(ls $DOWNDIR/20100916_c2_p?.07*.sorted.bam  $DOWNDIR/20100916_c2_p?.12*.sorted.bam $DOWNDIR/20100916_c2_p?.14*.sorted.bam)
	SORTBAM10_0=$(ls $DOWNDIR/20100916_c3_p?.02*.sorted.bam  $DOWNDIR/20100916_c3_p?.04*.sorted.bam $DOWNDIR/20100916_c3_p?.05*.sorted.bam)
	SORTBAM100_0=$(ls $DOWNDIR/20100916_c3_p?.07*.sorted.bam  $DOWNDIR/20100916_c3_p?.12*.sorted.bam $DOWNDIR/20100916_c3_p?.14*sorted.bam)

	VCFDIR=vcf/$DFRAC
	mkdir -p $VCFDIR
	SORT=($SORTBAM0_1 $SORTBAM0_3 $SORTBAM1_0 $SORTBAM10_0 $SORTBAM100_0)
	VCF=(vcf0_1 vcf0_3 vcf1_0 vcf10_0 vcf100_0)
	echo ---------------------------------------
	N=(0 1 2 3 4)
	echo ${N[@]:0:5}
	for i in ${N[@]:0:5}
	do	
		let h=6\*i
		echo ${SORT[@]:$h:6}
		echo ---------------------------------------
		echo SNP Calling
		if [ -f $VCFDIR/${VCF[$i]}.vcf ]
			then
				echo File  $VCFDIR/${VCF[$i]}.vcf exists already
			else
				samtools mpileup -C50 -d 1000000 -uDf $FASTAFILE ${SORT[@]:$h:6} | \
				bcftools view -bvcg - > $VCFDIR/${VCF[$i]}.bcf
				
				bcftools view $VCFDIR/${VCF[$i]}.bcf | \
				$VCFUTILS varFilter -D 1000000 > $VCFDIR/${VCF[$i]}.vcf
		fi 
	done
done
