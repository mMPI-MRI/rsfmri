# -*- coding: utf-8 -*-
"""
Created on Mon Oct 17 12:21:02 2016

@author: atschmidt
"""


from nipype.pipeline.engine import Node, Workflow 
import nipype.interfaces.utility as util
import nipype.interfaces.io as nio
import nipype.interfaces.fsl as fsl
import nipype.algorithms.rapidart as ra
from functions import motion_regressors, selectindex, nilearn_denoise, fix_hdr



# read in subjects and file names


subjects = [['P46','XXXX']]
sessions=['d0']

# directories
working_dir = '/nobackup/eminem2/schmidt/MMPIRS/preprocessing/working_dir'
out_dir = '/nobackup/eminem2/schmidt/MMPIRS/preprocessing/final/'

# main workflow
preproc_nuisance_regress = Workflow(name='func_preproc_nuisance_regress')
preproc_nuisance_regress.base_dir = working_dir
preproc_nuisance_regress.config['execution']['crashdump_dir'] = preproc_nuisance_regress.base_dir + "/crash_files"


# iterate over subjects
subject_infosource = Node(util.IdentityInterface(fields=['subjectlist']),
                  name='subject_infosource')
subject_infosource.iterables=[('subjectlist', subjects)]

# iterate over sessions
session_infosource = Node(util.IdentityInterface(fields=['session']),
                  name='session_infosource')
session_infosource.iterables=[('session', sessions)]

# select files

templates={'unwarped_file' : '/nobackup/eminem2/schmidt/MMPIRS/preprocessing/working_dir/func_preproc/_session_{session}/_subjectlist_{proband}.{subject}/fugue/corr_{subject}_{session}_S3_RS_ep2d_SMS6_TR1p1_TE22_FA40_1p2_FatSat_Echo_0_Te22_roi_unwarped.nii.gz',
           #'unwarped_file' : '/nobackup/eminem2/schmidt/MMPIRS/preprocessing/{subject}/fugue/corr_{subject}_{session}_S3_RS_ep2d_SMS6_TR1p1_TE22_FA40_1p2_FatSat_Echo_0_Te22_roi_unwarped.nii.gz',
           'slicemoco_par_file' : '/nobackup/eminem2/schmidt/MMPIRS/preprocessing/working_dir/func_preproc/_session_{session}/_subjectlist_{proband}.{subject}/spacetime_realign/{subject}_{session}_S3_RS_ep2d_SMS6_TR1p1_TE22_FA40_1p2_FatSat_Echo_0_Te22_roi.nii.gz.par',
           # need brain mask, csf and wm mask in functional space - from cbstools coreg pipeline 
#           'gm_mask' : '/nobackup/eminem2/schmidt/MMPIRS/preprocessing/{subject}/mappings/{subject}_{session}_S7_MP2RAGE_0p7_INV2_Te2_transform_clone_stripmask_clone_transform_def.nii.gz',
#           'gm_mask' : '/nobackup/eminem2/schmidt/MMPIRS/preprocessing/{subject}/masks/{subject}_{session}_brainmask_rsfmri.nii.gz',
           # use gm mask instead of gm 
           'gm_mask' : '/nobackup/eminem2/schmidt/MMPIRS/preprocessing/{subject}/masks/{subject}_{session}_GM_mask_rsfmri.nii.gz',
#           'csf_mask' : '/nobackup/eminem2/schmidt/MMPIRS/preprocessing/{subject}/mappings/{subject}_{session}_S5_MP2RAGE_0p7_T1_Images_Te2_clone_transform_strip_clone_reg_bound_seg_binmask_CSF_def.nii.gz',
#           'wm_mask' : '/nobackup/eminem2/schmidt/MMPIRS/preprocessing/{subject}/mappings/{subject}_{session}_S5_MP2RAGE_0p7_T1_Images_Te2_clone_transform_strip_clone_reg*_bound_seg_binmask_WM_def.nii.gz'}
           'csf_mask' : '/nobackup/eminem2/schmidt/MMPIRS/preprocessing/{subject}/masks/{subject}_{session}_CSF_mask_rsfmri.nii.gz',
           'wm_mask' : '/nobackup/eminem2/schmidt/MMPIRS/preprocessing/{subject}/masks/{subject}_{session}_WM_mask_corrected_rsfmri.nii.gz'}

selectfiles = Node(nio.SelectFiles(templates),
                   name="selectfiles")

preproc_nuisance_regress.connect([(subject_infosource, selectfiles, [(('subjectlist', selectindex, 0), 'subject'),
                                                    (('subjectlist', selectindex, 1), 'proband')]),
                 (session_infosource, selectfiles, [('session', 'session')])
                 ])

# set fsl output type to nii.gz
fsl.FSLCommand.set_default_output_type('NIFTI_GZ')




# fix header of brain mask
fix_header_brainmask = Node(util.Function(input_names=['data_file', 'header_file'],
                            output_names=['out_file'],
                            function=fix_hdr),
                  name='fix_header_brainmask')
preproc_nuisance_regress.connect([(selectfiles, fix_header_brainmask, [('gm_mask', 'data_file'),
                                        ('unwarped_file', 'header_file')]),
])


# fix header of csf mask
fix_header_csfmask = Node(util.Function(input_names=['data_file', 'header_file'],
                            output_names=['out_file'],
                            function=fix_hdr),
                  name='fix_header_csfmask')
preproc_nuisance_regress.connect([(selectfiles, fix_header_csfmask, [('csf_mask', 'data_file'),
                                        ('unwarped_file', 'header_file')]),
])    


# fix header of csf mask
fix_header_wmmask = Node(util.Function(input_names=['data_file', 'header_file'],
                            output_names=['out_file'],
                            function=fix_hdr),
                  name='fix_header_wmmask')
preproc_nuisance_regress.connect([(selectfiles, fix_header_wmmask, [('wm_mask', 'data_file'),
                                        ('unwarped_file', 'header_file')]),
])                       
                 

# merge images into list
masklist = Node(util.Merge(2),name='masklist')
preproc_nuisance_regress.connect([(fix_header_csfmask, masklist, [('out_file', 'in1')]),
                 (fix_header_wmmask, masklist, [('out_file', 'in2')]),
                 ])


# perform artefact detection
artefact=Node(ra.ArtifactDetect(save_plot=True,
                                use_norm=True,
                                parameter_source='NiPy',
                                mask_type='file',
                                norm_threshold=1,
                                zintensity_threshold=3,
                                use_differences=[True,False]
                                ),
             name='artefact')

preproc_nuisance_regress.connect([(selectfiles, artefact, [('unwarped_file', 'realigned_files'),
                                        ('slicemoco_par_file', 'realignment_parameters')]),
                 (selectfiles, artefact, [('gm_mask', 'mask_file')]),
                 ])

# calculate motion regressors

motreg = Node(util.Function(input_names=['motion_params', 'order','derivatives'],
                            output_names=['out_files'],
                            function=motion_regressors),
                 name='motion_regressors')
motreg.inputs.order=1
motreg.inputs.derivatives=1
preproc_nuisance_regress.connect([(selectfiles, motreg, [('slicemoco_par_file','motion_params')])])

def makebase(subject, out_dir):
    return out_dir + subject[1]
    
    
denoise = Node(util.Function(input_names=['in_file', 
                                          'gm_mask', 
                                          'wm_mask',
                                          'csf_mask',
                                          'motreg_file', 
                                          'outlier_file', 
                                          'bandpass', 
                                          'tr'],
                             output_names=['denoised_file',
                                           'confounds_file'],
                             function=nilearn_denoise),
               name='denoise')

denoise.inputs.tr = 1.13
denoise.inputs.bandpass = [0.1, 0.01]

preproc_nuisance_regress.connect([(selectfiles, denoise, [('unwarped_file', 'in_file')]),
                                  (fix_header_brainmask, denoise, [('out_file', 'gm_mask')]),
                                  (fix_header_wmmask, denoise, [('out_file', 'wm_mask')]),
                                  (fix_header_csfmask, denoise, [('out_file', 'csf_mask')]),                                 
                                 #(motreg, denoise, [('out_files', 'motreg_file')]),
                                 (motreg, denoise, [(('out_files',selectindex,[0]), 'motreg_file')]),
                                 (artefact, denoise, [('outlier_files', 'outlier_file')])])


# sink relevant files
sink = Node(nio.DataSink(parameterization=False),
             name='sink')

preproc_nuisance_regress.connect([(session_infosource, sink, [('session', 'container')]),
                 (subject_infosource, sink, [(('subjectlist', makebase, out_dir), 'base_directory')]),
                (fix_header_brainmask, sink, [('out_file', 'confounds@new_brainmask_header')]),
                (fix_header_csfmask, sink, [('out_file', 'confounds@new_csfmask_header')]),
                (fix_header_wmmask, sink, [('out_file', 'confounds@new_wmmask_header')]),
                (artefact, sink, [('norm_files', 'confounds.@norm_motion'),
                                  ('outlier_files', 'confounds.@outlier_files'),
                                  ('intensity_files', 'confounds.@intensity_files'),
                                  ('statistic_files', 'confounds.@outlier_stats'),
                                  ('plot_files', 'confounds.@outlier_plots')]),
                 (motreg, sink, [('out_files', 'confounds.@motreg')]),
                 (denoise, sink, [('denoised_file', 'final.@final'),
                                  ('confounds_file', 'confounds.@all')])])



#preproc_nuisance_regress.run(plugin='MultiProc', plugin_args={'n_procs' : 9})
preproc_nuisance_regress.run()

#preproc_nuisance_regress.write_graph(dotfilename='func_preproc_nuisance_regress.dot', graph2use='colored', format='pdf', simple_form=True)
