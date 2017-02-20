

%von Julia: 

%data = '/data/pt_nro160/DOPING/probands/';
%file= '/preprocessed/doping_resting/rest2/rest_preprocessed2mni_smoothed_msk.nii.gz';
%subjects= {'P23','P24','P25','P26','P27','P28','P29','P30','P31','P32','P33','P34','P35','P36','P37','P38','P39','P40','P41','P42','P43','P44'
%    'P01','P02','P03','P04','P05','P06','P07','P08','P09','P10','P11','P12','P13','P14','P15','P16','P17','P18','P19','P20','P21','P22'
%    };


%for i= 1:length(subjects)
%   dir(i)=strcat (data,subjects(i),file)
%   dirmat= cell2mat(dir(i))
%   fastECM([dirmat],1,1,1,16)
%end;


data = '/nobackup/eminem2/schmidt/MMPIRS/fastECM/';
file= '/d6_preprocessed.nii.gz';


subjects={'P05','P06','P07','P08','P09','P10','P11','P12','P13','P14','P15','P16','P17','P18','P20','P21','P22','P23','P24','P25','P26','P27','P28','P30','P31','P32','P33','P34','P35','P36','P37','P38','P39','P40','P41','P42','P43','P44','P45','P46'};


for i= 1:length(subjects)
   dir(i)=strcat(data,subjects(i),file)
   dirmat= cell2mat(dir(i))
   fastECM([dirmat],0,0,0,16)
end;

%for i= 1:length(subjects)
%   dir(i)=strcat (data,subjects(i),subjects(i)_file)
%   dirmat= cell2mat(dir(i))
%   fastECM([dirmat],1,1,1,16)
%end;