# FOR MID TASK, School study Baseline (gr5)

# Sarah 2020 B&M Lab
# you need to have the gsed version of sed added to your bash profile
# can install it with brew install gnu-sed, then add to path.

#scriptshell modeled from Matt's stroop analysis (on server)

#Skull-stripping scripts are under /scripts on the server


import os,sys
import argparse
import numpy as np
import re
from datetime import datetime
from subprocess import call
from subprocess import check_output
import csv

#parse command line arguments

parser = argparse.ArgumentParser()

parser.add_argument("--nopre",help="skip all preprocessing steps", action="store_true")
parser.add_argument("--noconvert",help="skip converting from DICOM to NIFTI", action="store_true")
parser.add_argument("--nobet",help="skip brain extraction", action="store_true")
parser.add_argument("--noreg",help="skip registration copying", action="store_true")
parser.add_argument("--nofirst",help="skip first level feat", action="store_true")
parser.add_argument("--nosecond",help="skip second level feat", action="store_true")
parser.add_argument("--nomotion",help="skip motion report", action="store_true")

args = parser.parse_args()

#paths(Change as needed)

datafolder = "/Volumes/MusicProject/Individual_Projects/Sarah.H/SchoolStudypractice/Functional/Gr5/Baseline3"
if not os.path.exists(datafolder):
	datafolder = "/Volumes/MusicProject-1/Individual_Projects/Sarah.H/SchoolStudypractice/Functional/Gr5/Baseline3/"


genericdesign_scrub = "%s/designs/generic_firstlevel_MID_scrub.fsf" %(datafolder)
genericdesign_noscrub = "%s/designs/firstlevel_MID_design_noscrub.fsf" %(datafolder)


secondleveldesign = "%s/designs/secondlevel_MID_design.fsf" %(datafolder)

#set analysis values
numconfounds = 8
smoothmm = 5	#smoothing sigma fwhm in mm
smoothsigma = smoothmm/2.3548	#convert to sigma
additive = 10000	#value added to distinguish brain from background
brightnessthresh = additive * .75


count = 0


groupList = ['Control', 'Music']

for group in groupList:

		subjectDir = "%s/%s/" %(datafolder,group)

		subjectList = [elem for elem in os.listdir(subjectDir) if "." not in elem]


		#Excludes
		excludeList = ["540MM", "541IG","542JL", "568RM", "571LA"]
		subjectList = [elem for elem in subjectList if elem not in excludeList]

		subjectList.sort()



		for subj in subjectList:
			subject = subj

			subjfolder = subjectDir + subject + "/"

			logfile = subjfolder + "analysis_log.txt"
			checkevfile = subjfolder + "winhigh_incorrect_run1.txt"
			finalfile = subjfolder + "secondlevel_cor_MID.gfeat/cope1.feat"

			if os.path.exists(finalfile):
				count = count + 1
				print(count,group,subject,finalfile)

			#Skip this subject if they do not have ev files
			if not os.path.exists(checkevfile):
				print("The subject %s has no EV Files. Moving on")
				continue




			mprage = subjfolder + "mprage.nii.gz"
			t1image = subjfolder + "mprage_brain.nii.gz"
			fieldmap_phase_rad = subjfolder + "fieldmap_phase_rad.nii.gz"



			####################
			## Brain Extraction
			####################

			print("###############################")
			print("BRAIN EXTRACTION, COMMENCING")

			fieldmap_phase_file = subjfolder + "fieldmap_phase.nii.gz"
			fieldmap_mag_brain_file = subjfolder + "fieldmap_mag_brain.nii.gz"
			fieldmap_phase_rad_file = subjfolder + "fieldmap_phase_rad.nii.gz"
			fieldmap_phase_rad = subjfolder + "fieldmap_phase_rad.nii.gz"



			if not args.nobet:
				if not os.path.exists(fieldmap_phase_rad):
					print("Skull stripping field map mag for %s" %subj)
					command = "%s/scripts/skullstrip_field.py %s" %(datafolder,subjfolder)
					print(command)
					call(command,shell = True)


					print("preparing field maps for %s" %subj)
					command = "fsl_prepare_fieldmap SIEMENS %s %s %s 2.5" %(fieldmap_phase_file, fieldmap_mag_brain_file,fieldmap_phase_rad_file)
					call(command, shell = True)


				else:
					print("Fieldmap prep already done for this subject. Moving on!")

				if not os.path.exists(t1image):
					print("Skull Stripping mprage for %s" %subj)
					command = "%s/scripts/skullstrip.py %s" %(datafolder,subjfolder)
					print(command)
					call(command,shell = True)
				else:
					print("T1 prep already done for this subject. Moving on!")





				####################
				# First level analysis
				####################

			if not args.nofirst:

					for run in range(1,3):
						print("we are on run...%d" %run)


						firstlevel_featfolder = subjfolder + "firstlevel_MID_run%d.feat" %(run)
						inputfile = subjfolder + "MID_run%d.nii.gz" %(run)
						designOutput = subjfolder + "firstlevel_MID_design_run%d.fsf" %(run)

						checkfile = firstlevel_featfolder + "/rendered_thresh_zstat4.nii.gz"


						print("###############################")
						print("SCRUB-A-DUB DUBBING")


						scrubout = subjfolder + "scrub_confounds_MID_run%d" %(run)
						command = "fsl_motion_outliers -i %s -o %s" %(inputfile, scrubout)

						if not args.nobet:
							if not os.path.exists(scrubout):
								print("scrubbing for %s run %d" %(subj, run))
								#command = "%sscripts/skullstrip.py %s" %(datafolder,subjfolder)
								print(command)
								call(command,shell = True)
								print("i completed scrubbing for %s run %d" %(subj, run))

							else:
								print("scrubbing already done for this one! moving on.")


						#####################

						## FIRST LEVEL FEAT!!!

						#####################
						print("###############################")
						print("FIRST LEVEL FEAT, COMMENCING")

						print("First level FEAT Analysis for: %s, run: %d" %(subject,run))
						if os.path.exists(checkfile):
							print(checkfile)
							print("First level feat analysis already completed for %s, run %d. Moving on." %(subject,run))
							continue

						if not os.path.exists(inputfile):
							print("Run %s for subject %s does not exist or is not in folder. Moving on.%s" %(run,subject))
							continue


						command = 'fslinfo %s' %(inputfile)
						results = check_output(command,shell=True)
						numtimepoints_1 = results.split()[9]

						numtimepoints = numtimepoints_1.decode()
						print("Number of volumes: %s" %(numtimepoints))

						#set up evfiles
						evfile1 = subjfolder + "losehigh_incorrect_run%d.txt" %(run)
						evfile2 = subjfolder + "losehigh_correct_run%d.txt" %(run)
						evfile3 = subjfolder + "loselow_incorrect_run%d.txt" %(run)
						evfile4 = subjfolder + "loselow_correct_run%d.txt" %(run)
						evfile5 = subjfolder + "neutral_run%d.txt" %(run)
						evfile6 = subjfolder + "winhigh_incorrect_run%d.txt" %(run)
						evfile7 = subjfolder + "winhigh_correct_run%d.txt" %(run)
						evfile8 = subjfolder + "winlow_incorrect_run%d.txt" %(run)
						evfile9 = subjfolder + "winlow_correct_run%d.txt" %(run)

						print(sectionColor + "This subject has a scrub folder %s%s" %(scrubout,mainColor))

						command = 'gsed -e "s|DEFINEINPUT|%s|g" -e "s|DEFINEOUTPUT|%s|g" -e "s|DEFINESCRUB|%s|g" -e "s|DEFINEPHASERAD|%s|g" -e "s|DEFINEPHASEMAG|%s|g" -e "s|DEFINESTRUCT|%s|g" -e "s|DEFINEVOLUME|%s|g" -e "s|DEFINEEVFILE1|%s|g" -e "s|DEFINEEVFILE2|%s|g" -e "s|DEFINEEVFILE3|%s|g" -e "s|DEFINEEVFILE4|%s|g" -e "s|DEFINEEVFILE5|%s|g" -e "s|DEFINEEVFILE6|%s|g" -e "s|DEFINEEVFILE7|%s|g" -e "s|DEFINEEVFILE8|%s|g" -e "s|DEFINEEVFILE9|%s|g" %s>%s' %(re.escape(inputfile),re.escape(firstlevel_featfolder), re.escape(scrubout),re.escape(fieldmap_phase_rad), re.escape(fieldmap_mag_brain_file),re.escape(t1image), numtimepoints,re.escape(evfile1),re.escape(evfile2), re.escape(evfile3), re.escape(evfile4), re.escape(evfile5),re.escape(evfile6),re.escape(evfile7), re.escape(evfile8), re.escape(evfile9),genericdesign_scrub,designOutput)

						call(command, shell = True)

						print(designOutput)
						command = "feat %s" %designOutput
						call(command, shell = True)

						print('i have finished first level feating for %s run: %d' %(subject, run))


			####################
			# Second level analysis
			####################



			if not args.nosecond:

				secondlevel_folder = subjfolder + "secondlevel_MID.gfeat"
				feat1 = subjfolder + 'firstlevel_MID_run1.feat'
				feat2 = subjfolder + 'firstlevel_MID_run2.feat'

				if not os.path.exists(feat1) or not os.path.exists(feat2):
						print (sectionColor + "One or more first level feat folders did not complete correctly or does not exist for subject %s. Moving on.%s" %(subject,mainColor))
						continue

				checkcopefolder = secondlevel_folder + "/cope5.feat/rendered_thresh_zstat1.nii.gz"

				print (sectionColor2 + "Second Level Analysis for: %s%s"  %(subject,mainColor))

				if not os.path.exists(checkcopefolder):
					designOutput2 = subjfolder + "secondlevel_MID_design.fsf"
					command = "gsed -e 's|DEFINEOUTPUT|%s|g' -e 's|DEFINEFEAT1|%s|g' -e 's|DEFINEFEAT2|%s|g' %s > %s" %(re.escape(secondlevel_folder),re.escape(feat1), re.escape(feat2),secondleveldesign,designOutput2)

					call(command, shell = True)
					command = "feat %s" % designOutput2
					call(command, shell= True)
					print('i have finished second level feating for %s' %subject)

				else:

					print(sectionColor + "Second level for %s already completed, moving on %s\n"  %(subject,mainColor))


print("################")
print("ALL DONE! GO TAKE A LOOK @ YOUR DATA!!!!")
print("################")
