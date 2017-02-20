# -*- coding: utf-8 -*-
"""
Created on Mon Oct 10 17:51:07 2016

@author: atschmidt
"""

from nipype.pipeline.engine import Node, Workflow 
import nipype.interfaces.utility as util
import nipype.interfaces.io as nio
import nipype.interfaces.nipy as nipy
import nipype.interfaces.fsl as fsl
from functions import strip_rois_func, selectindex, median
from nipype.algorithms.misc import TSNR

# read in subjects and file names

subjects = [['XXXX','P46']]

sessions=['d1']

# directories
working_dir = '/nobackup/eminem2/schmidt/MMPIRS/preprocessing/working_dir'
#data_dir = '/nobackup/monaco1/schmidt/MMPIRS/preprocessed'
#data_dir = '/afs/cbs.mpg.de/projects/neu009_sequencing-plasticity/probands'
out_dir = '/nobackup/eminem2/schmidt/MMPIRS/preprocessing/'

# set fsl output type to nii.gz
fsl.FSLCommand.set_default_output_type('NIFTI_GZ')

# volumes to remove from each timeseries
vol_to_remove = 5

# main workflow
preproc = Workflow(name='func_preproc')
preproc.base_dir = working_dir
preproc.config['execution']['crashdump_dir'] = preproc.base_dir + "/crash_files"

# iterate over subjects
subject_infosource = Node(util.IdentityInterface(fields=['subjectlist']),
                  name='subject_infosource')
subject_infosource.iterables=[('subjectlist', subjects)]

# iterate over sessions
session_infosource = Node(util.IdentityInterface(fields=['session']),
                  name='session_infosource')
session_infosource.iterables=[('session', sessions)]

# select files

templates={'rest' : '/afs/cbs.mpg.de/projects/neu009_sequencing-plasticity/probands/{subject}/{session}/{proband}_{session}_S3_RS_ep2d_SMS6_TR1p1_TE22_FA40_1p2_FatSat_Echo_0_Te22.nii.gz',
           'phase1' : '/afs/cbs/projects/neu009_sequencing-plasticity/probands/{subject}/{session}/{proband}_{session}_S14_gre_phase_ref_corrected_gre_phase_sum_Te4.08.nii.gz',
	   'phase2' : '/afs/cbs/projects/neu009_sequencing-plasticity/probands/{subject}/{session}/{proband}_{session}_S14_gre_phase_ref_corrected_gre_phase_sum_Te9.18.nii.gz',
           'mag1' : '/afs/cbs/projects/neu009_sequencing-plasticity/probands/{subject}/{session}/{proband}_{session}_S12_gre_phase_ref_corrected_gre_magnitude_sum_Te4.08.nii.gz'}

selectfiles = Node(nio.SelectFiles(templates),
                   name="selectfiles")

preproc.connect([(subject_infosource, selectfiles, [(('subjectlist', selectindex, 0), 'subject'),
                                                    (('subjectlist', selectindex, 1), 'proband')]),
                 (session_infosource, selectfiles, [('session', 'session')])
                 ])

# remove first volumes
remove_vol = Node(util.Function(input_names=['in_file','t_min'],
                                output_names=["out_file"],
                                function=strip_rois_func),
                   name='remove_vol')
remove_vol.inputs.t_min = vol_to_remove

preproc.connect([(selectfiles, remove_vol, [('rest', 'in_file')])])





brain_extract_mag1 = Node(fsl.BET(), name='brain_extract_mag1')

preproc.connect([(selectfiles, brain_extract_mag1, [('mag1', 'in_file')])])


# simultaneous slice time and motion correction
slicemoco = Node(nipy.SpaceTimeRealigner(),
                 name="spacetime_realign")


preproc.connect([(remove_vol, slicemoco, [('out_file', 'in_file')])])


# compute first tsnr and detrend
tsnr = Node(TSNR(regress_poly=2),
               name='tsnr')
preproc.connect([(slicemoco, tsnr, [('out_file', 'in_file')])])

# compute median of realigned timeseries for preperation for fieldmap

median1 = Node(util.Function(input_names=['in_files'],
                       output_names=['median_file'],
                       function=median),name='median1')

#median = Node(SpatialFilter(operation='median'),
#              name='median')


preproc.connect([(tsnr, median1, [('detrended_file', 'in_files')])])


#prelude phase unwrapping x 2 

prelude1 = Node(fsl.PRELUDE(terminal_output='none'),
                            name='prelude1')

                  
preproc.connect([(selectfiles, prelude1, [('phase1', 'phase_file')]),
                 (brain_extract_mag1, prelude1, [('out_file', 'magnitude_file')])])

prelude2 = Node(fsl.PRELUDE(terminal_output='none'),
                            name='prelude2')

                  
preproc.connect([(selectfiles, prelude2, [('phase2', 'phase_file')]),
                 (brain_extract_mag1, prelude2, [('out_file', 'magnitude_file')])])



# Getting the fieldmap in rad/s ---- fusing phase images -sub -mul 1000 -div 5,10

phase_maths_sub = Node(fsl.BinaryMaths(operation='sub'),
                                   name='phase_maths_sub')
preproc.connect([(prelude1, phase_maths_sub, [('unwrapped_phase_file', 'in_file')]),
                 (prelude2, phase_maths_sub, [('unwrapped_phase_file', 'operand_file')]),
                 ])

phase_maths_mul = Node(fsl.BinaryMaths(operation='mul',
                                   operand_value=1000.0),
                                   name='phase_maths_mul')
preproc.connect([(phase_maths_sub, phase_maths_mul, [('out_file', 'in_file')])])


phase_maths_div = Node(fsl.BinaryMaths(operation='div',
                                   operand_value=5.10),
                                   name='phase_maths_div')
preproc.connect([(phase_maths_mul, phase_maths_div, [('out_file', 'in_file')])])


# make transformation map to register fieldmap FLIRT

flirtmag2rsfmri_map = Node(fsl.FLIRT(dof=6),
                  name='flirtmag2rsfmri_map')

#preproc.connect(templates,'mag1',flirtmag2rsfmri_map,'in_file')
#preproc.connect(median,'out_file',flirtmag2rsfmri_map,'reference')

preproc.connect([(brain_extract_mag1, flirtmag2rsfmri_map, [('out_file','in_file')]),
                 (median1, flirtmag2rsfmri_map, [('median_file','reference')]),
                 ])
        
                  
# use transformation as reference to register phase images - FLIRT again

phase_reg = Node(fsl.FLIRT(cost_func='mutualinfo',
                   apply_xfm=True),
                   name='phase_reg')
                   
preproc.connect([(phase_maths_div, phase_reg, [('out_file', 'in_file')]),
                 (median1, phase_reg, [('median_file', 'reference')]),
                 (flirtmag2rsfmri_map, phase_reg, [('out_matrix_file', 'in_matrix_file')]),
                 ])


#FUGUE

fugue = Node(fsl.FUGUE(dwell_time=0.00076,
                       unwarp_direction='y'),
                       name='fugue')
                                              
preproc.connect([(slicemoco, fugue, [('out_file','in_file')]),
                 (phase_reg, fugue, [('out_file','fmap_in_file')])])
                 

# compute second tsnr and detrend then brain extract tsnr file 
tsnr_unwarped = Node(TSNR(regress_poly=2, tsnr_file='P46_d1_unwarped_tsnr.nii.gz'),
               name='tsnr_unwarped')
preproc.connect([(fugue, tsnr_unwarped, [('unwarped_file', 'in_file')])])         


brain_extract_tsnr_unwarped = Node(fsl.BET(), name='brain_extract_tsnr_unwarped')

preproc.connect([(tsnr_unwarped, brain_extract_tsnr_unwarped, [('tsnr_file', 'in_file')])])    

# compute median_unwarped of unwarped timeseries for coregistration to anatomy

median_unwarped = Node(util.Function(input_names=['in_files'],
                       output_names=['median_file'],
                       function=median),
                       name='median_unwarped')

preproc.connect([(fugue, median_unwarped, [('unwarped_file', 'in_files')])])





def makebase(subject, out_dir):
    return out_dir + subject[1]

# sink relevant files
sink = Node(nio.DataSink(parameterization=False),
             name='sink')

preproc.connect([(session_infosource, sink, [('session', 'container')]),
                 (subject_infosource, sink, [(('subjectlist', makebase, out_dir), 'base_directory')]),
                 (slicemoco, sink, [('out_file', 'realignment.@realigned_file'),
                                    ('par_file', 'confounds.@orig_motion')]),
                 (tsnr, sink, [('tsnr_file', 'realignment.@tsnr')]),
                 (median1, sink, [('median_file', 'realignment.@median')]),
                 (prelude1, sink, [('unwrapped_phase_file', 'confounds.@prelude1')]),
                 (prelude2, sink, [('unwrapped_phase_file', 'confounds.@prelude2')]),
                 (phase_maths_sub, sink, [('out_file', 'confounds.@maths_sub')]),
                 (phase_maths_mul, sink, [('out_file', 'confounds.@maths_mul')]),
                 (phase_maths_div, sink, [('out_file', 'confounds.@maths_div_end_maths')]),
                 (flirtmag2rsfmri_map,sink, [('out_file', 'confounds.@flirt_mag2rsfmri')]),
                 (phase_reg, sink, [('out_file', 'confounds.@flirt_phase2rsfmri'),
                                    ('out_log', 'confounds.@phase_reg_log'),
                                    ('out_matrix_file', 'confounds.@out_matrix_file')]),
                (fugue, sink, [('fmap_out_file', 'confounds.@fmap_out'),
                                  ('shift_out_file', 'confounds.@shift_out_file'),
                                  ('unwarped_file', 'confounds.@ST_Moco_Fmap_corr_file')]),
                 (tsnr_unwarped, sink, [('tsnr_file', 'realignment.@tsnr_unwarped')]),
                (median_unwarped, sink, [('median_file', 'confounds.@median_unwarped_file')])])

#preproc.run(plugin='MultiProc', plugin_args={'n_procs' : 9})
preproc.run()
#preproc.write_graph(dotfilename='func_preproc.dot', graph2use='colored', format='pdf', simple_form=True)
