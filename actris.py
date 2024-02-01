import os
import logging
import datetime
import sys
import glob
import xml.etree.ElementTree as ET
import subprocess
import netCDF4 as nc
import numpy as np
import shutil
import math
import numpy.ma as ma
import softio
import fpsim

FLEXPART_ROOT   = "/usr/local/flexpart_v10.4_3d7eebf"
FLEXPART_EXE    = "/usr/local/flexpart_v10.4_3d7eebf/src/FLEXPART"

STATIONS_CODE = {"PicDuMidi":"PDM",
                 "PuyDeDome":"PUY",
                 "SIRTA":"SAC",
                 "ObservatoirePerenne":"OPE",
                 "Maido":"RUN",
                 "Lamto":"LTO"}

def write_header_in_file(filepath: str) -> None:
    with open(filepath,"w") as file:
        file.write("╔═══════════════════════════════════════════════╗\n")
        file.write("║                 |    *                        ║\n")
        file.write("║                 |  *                          ║\n")
        file.write("║                 | *                           ║\n")
        file.write("║             ,,gg|dY\"\"\"\"Ybbgg,,                ║\n")
        file.write("║        ,agd\"\"'  |           `\"\"bg,            ║\n")
        file.write("║     ,gdP\"     A C T R I S       \"Ybg,         ║\n")
        file.write("║                     FRANCE                    ║\n")
        file.write("╚═══════════════════════════════════════════════╝\n")

def print_header_in_terminal() -> None:
    LOGGER.info("╔═══════════════════════════════════════════════╗")
    LOGGER.info("║                 |    *                        ║")
    LOGGER.info("║                 |  *                          ║")
    LOGGER.info("║                 | *                           ║")
    LOGGER.info("║             ,,gg|dY\"\"\"\"Ybbgg,,                ║")
    LOGGER.info("║        ,agd\"\"'  |           `\"\"bg,            ║")
    LOGGER.info("║     ,gdP\"     A C T R I S       \"Ybg,         ║")
    LOGGER.info("║                     FRANCE                    ║")
    LOGGER.info("╚═══════════════════════════════════════════════╝")

def start_log(shell_option: bool=True, log_filepath: str="") -> logging.Logger:
    log_handlers = []
    if shell_option==True:
        log_handlers.append(logging.StreamHandler())
    log_handlers.append(logging.FileHandler(log_filepath))
    logging.basicConfig(format="%(asctime)s   [%(levelname)s]   %(message)s",
                        datefmt="%d/%m/%Y %H:%M:%S",
                        handlers=log_handlers)
    logger = logging.getLogger('my_log')
    logger.setLevel(logging.DEBUG)
    return logger

def verif_xml_file(xml_filepath: str) -> None:
    LOGGER.info("Checking "+os.path.basename(xml_filepath)+" file")
    if not os.path.exists(xml_filepath):
        LOGGER.error(os.path.basename(xml_filepath)+" file does not exist")
        sys.exit(1)

def get_simulation_date(xml_file: str) -> dict:
    xml  = ET.parse(xml_file)
    # ________________________________________________________
    # Check if all nodes are present
    xml_nodes = ["actris/simulation_date",
                 "actris/simulation_date/begin",
                 "actris/simulation_date/end",
                 "actris/simulation_date/dtime"]
    for node in xml_nodes:
        try:
            found_node = xml.getroot().find(node)
        except:
            LOGGER.error("<simulation_date> node is missing or its children nodes are in incorrect format, check your configuration file!")
            sys.exit(1)
    # ________________________________________________________
    # Get date from the xml
    xml  = xml.getroot().find("actris").find("simulation_date")
    date = {}
    date["begin"] = xml.find("begin").text
    date["end"]   = xml.find("end").text
    date["dtime"] = int(xml.find("dtime").text)
    # ________________________________________________________
    # Check if strings are correct
    try:
        begin_date = datetime.datetime.strptime(date["begin"],"%Y%m%d")
    except:
        LOGGER.error("Begin date of the simulation is incorrect. Correct pattern : YYYYMMDD")
        sys.exit(1)
    try:
        end_date = datetime.datetime.strptime(date["end"],"%Y%m%d")
    except:
        LOGGER.error("End date of the simulation is incorrect. Correct pattern : YYYYMMDD")
        sys.exit(1)
    # if (date["dtime"]!=3) and (date["dtime"]!=6):
    #     LOGGER.error("ECMWF delta step of the data should be either 3 or 6 hours, check your configuration file!")
    #     sys.exit(1)
    if begin_date > end_date:
        LOGGER.error("Begin date have to be earlier that the end date or be equal to the end date, check your configuration file")
        sys.exit(1)
    return date

def get_simulation_time(xml_file: str) -> dict:
    simul_date = get_simulation_date(xml_file)
    xml  = ET.parse(xml_file)
    # ________________________________________________________
    # Check if all nodes are present
    xml_nodes = ["actris/simulation_time",
                 "actris/simulation_time/begin",
                 "actris/simulation_time/end"]
    for node in xml_nodes:
        try:
            found_node = xml.getroot().find(node)
        except:
            LOGGER.error("<simulation_time> node is missing or its children nodes are in incorrect format, check your configuration file!")
            sys.exit(1)
    # ________________________________________________________
    # Get time from the xml file
    xml  = xml.getroot().find("actris").find("simulation_time")
    time = {}
    time["begin"] = xml.find("begin").text
    time["end"]   = xml.find("end").text
    # ________________________________________________________
    # Check if strings are correct
    try:
        begin_time = datetime.datetime.strptime(simul_date["begin"]+"-"+time["begin"],"%Y%m%d-%H%M%S")
    except:
        LOGGER.error("Begin time of the simulation is incorrect. Correct pattern : HHMMSS")
        sys.exit(1)
    try:
        end_time = datetime.datetime.strptime(simul_date["end"]+"-"+time["end"],"%Y%m%d-%H%M%S")
    except:
        LOGGER.error("End time of the simulation is incorrect. Correct pattern : HHMMSS")
        sys.exit(1)
    if begin_time > end_time:
        LOGGER.error("Begin and end date/time of the simulation are inconsistent; begin date and time of the simulation should always be before the end date and time of the simulation; check your configuration file!")
        sys.exit(1)
    return time

def write_available_file(config_xml_filepath: str, working_dir: str) -> None:
    LOGGER.info("Preparing AVAILABLE file for FLEXPART")
    simul_date = get_simulation_date(config_xml_filepath)
    # 	20120101 000000      EA12010100      ON DISK
    start_date = datetime.datetime.strptime(simul_date["begin"]+"T00:00:00","%Y%m%dT%H:%M:%S")
    end_date   = datetime.datetime.strptime(simul_date["end"]+"T23:59:59","%Y%m%dT%H:%M:%S")
    hour_delta = datetime.timedelta(hours=simul_date["dtime"])
    file_date  = start_date
    with open(working_dir+"/AVAILABLE","w") as file:
        file.write("XXXXXX EMPTY LINES XXXXXXXXX\n")
        file.write("XXXXXX EMPTY LINES XXXXXXXXX\n")
        file.write("YYYYMMDD HHMMSS   name of the file(up to 80 characters)\n")
        while file_date < end_date:
            line = ""
            line = line + datetime.datetime.strftime(file_date,"%Y%m%d") + " "
            line = line + datetime.datetime.strftime(file_date,"%H%M%S") + "      "
            line = line + "EN" + datetime.datetime.strftime(file_date,"%y%m%d%H") + "      "
            line = line + "ON DISK\n"
            file.write(line)
            file_date = file_date + hour_delta

def get_ECMWF_pool_path(config_xml_filepath: str) -> str:
    xml  = ET.parse(config_xml_filepath)
    return xml.getroot().find("actris").find("paths").find("ecmwf_dir").text

def write_pathnames_file(config_xml_filepath: str, working_dir: str) -> None:
    # options_folder/
    # output_folder/
    # ECMWF_data_folder/
    # path_to_AVAILABLE_file/AVAILABLE
    LOGGER.info("Preparing pathnames file for FLEXPART")
    with open(working_dir+"/pathnames","w") as file:
        file.write(wdir+"/options/\n")
        file.write(wdir+"/output/\n")
        file.write(get_ECMWF_pool_path(config_xml_filepath)+"\n")
        file.write(wdir+"/AVAILABLE")

def write_command_file(config_xml_filepath: str, working_dir: str) -> None:
    LOGGER.info("Preparing COMMAND file for FLEXPART")
    xml  = ET.parse(config_xml_filepath)
    xml  = xml.getroot().find("actris")
    xml_keys = ["flexpart/command/forward",
                "simulation_date/begin",
                "simulation_time/begin",
                "simulation_date/end",
                "simulation_time/end",
                "flexpart/command/time/output",
                "flexpart/command/time/averageOutput",
                "flexpart/command/time/sampleRate",
                "flexpart/command/time/particleSplitting",
                "flexpart/command/time/synchronisation",
                "flexpart/command/ctl",
                "flexpart/command/ifine",
                "flexpart/command/iOut",
                "flexpart/command/ipOut",
                "flexpart/command/lSubGrid",
                "flexpart/command/lConvection",
                "flexpart/command/lAgeSpectra",
                "flexpart/command/ipIn",
                "flexpart/command/iOfr",
                "flexpart/command/iFlux",
                "flexpart/command/mDomainFill",
                "flexpart/command/indSource",
                "flexpart/command/indReceptor",
                "flexpart/command/mQuasilag",
                "flexpart/command/nestedOutput",
                "flexpart/command/lInitCond",
                "flexpart/command/surfOnly",
                "flexpart/command/cblFlag"]
    flexpart_keys = ["LDIRECT","IBDATE","IBTIME","IEDATE","IETIME","LOUTSTEP","LOUTAVER","LOUTSAMPLE","ITSPLIT","LSYNCTIME","CTL",
                     "IFINE","IOUT","IPOUT","LSUBGRID","LCONVECTION","LAGESPECTRA","IPIN","IOUTPUTFOREACHRELEASE","IFLUX","MDOMAINFILL",
                     "IND_SOURCE","IND_RECEPTOR","MQUASILAG","NESTED_OUTPUT","LINIT_COND","SURF_ONLY","CBLFLAG"]
    # ----------------------------------------------------
    # MANUAL VERSION
    # ----------------------------------------------------
    with open(working_dir+"/options/COMMAND","w") as file:
        file.write("***************************************************************************************************************\n")
        file.write("*                                                                                                             *\n")
        file.write("*      Input file for the Lagrangian particle dispersion model FLEXPART                                       *\n")
        file.write("*                           Please select your options                                                        *\n")
        file.write("*                                                                                                             *\n")
        file.write("***************************************************************************************************************\n")
        file.write("&COMMAND\n")
        for ii in range(len(xml_keys)):
            try:
                value = xml.find(xml_keys[ii]).text
            except:
                LOGGER.error(f"<{xml_keys[ii]}> node is missing, check your configuration file!")
            file.write(" "+
                       flexpart_keys[ii]+"="+
                       " "*(24-len(flexpart_keys[ii])-1-len(value))+
                       value+
                       ",\n")
        file.write(" OHFIELDS_PATH=\""+FLEXPART_ROOT+"/flexin\",\n")
        file.write(" /\n")

def write_outgrid_file(config_xml_filepath: str, working_dir: str) -> None:
    LOGGER.info("Preparing OUTGRID file for FLEXPART")
    xml  = ET.parse(config_xml_filepath)
    # ________________________________________________________
    # Check if all nodes are present
    xml_nodes = ["actris/flexpart/outGrid",
                 "actris/flexpart/outGrid/longitude/min",
                 "actris/flexpart/outGrid/longitude/max",
                 "actris/flexpart/outGrid/latitude/min",
                 "actris/flexpart/outGrid/latitude/max",
                 "actris/flexpart/outGrid/resolution"]
    for node in xml_nodes:
        try:
            found_node = xml.getroot().find(node)
        except:
            LOGGER.error("<flexpart/outGrid> node is missing or its children nodes are in incorrect format, check your configuration file!")
            sys.exit(1)
    # ________________________________________________________
    # Get data from the xml file
    xml  = xml.getroot().find("actris/flexpart/outGrid")
    Nx = int((float(xml.find("longitude/max").text) - float(xml.find("longitude/min").text))/float(xml.find("resolution").text))
    Ny = int((float(xml.find("latitude/max").text) - float(xml.find("latitude/min").text))/float(xml.find("resolution").text))
    height_levels = [node.text for node in xml.find("height")]
    # ________________________________________________________
    # Check if data is correct
    # if (float(xml.find("longitude/max").text)>180) or (float(xml.find("longitude/min").text)<-180):
    #     LOGGER.error("Minimim or maximum longitude are out of possible range (-180 deg ; +180 deg), check your configuration file!")
    #     sys.exit(1)
    if (float(xml.find("latitude/max").text)>90) or (float(xml.find("latitude/min").text)<-90):
        LOGGER.error("Minimim or maximum latitude are out of possible range (-90 deg ; +90 deg), check your configuration file!")
        sys.exit(1)
    if (Nx<=0) or (Ny<=0):
        LOGGER.error("Minimum latitude and longitude should always be inferior to the maximum values, resolution should be consistent with chosen lat/lon window to avoid zero-size image in X and Y direction, check your configuration file!")
        sys.exit(1)
    if float(xml.find("resolution").text)<=0:
        LOGGER.error("Spatial resolution should be positive, check your configuration file!")
        sys.exit(1)
    check_height_levels = [float(elem)<0 for elem in height_levels]
    if np.any(check_height_levels):
        LOGGER.error("Height values can only be positive, check your configuration file!")
        sys.exit(1)
    # ________________________________________________________
    # Write OUTGRID file
    with open(working_dir+"/options/OUTGRID","w") as file:
        file.write("!*******************************************************************************\n")
        file.write("!                                                                              *\n")
        file.write("!      Input file for the Lagrangian particle dispersion model FLEXPART        *\n")
        file.write("!                       Please specify your output grid                        *\n")
        file.write("!                                                                              *\n")
        file.write("! OUTLON0    = GEOGRAPHYICAL LONGITUDE OF LOWER LEFT CORNER OF OUTPUT GRID     *\n")
        file.write("! OUTLAT0    = GEOGRAPHYICAL LATITUDE OF LOWER LEFT CORNER OF OUTPUT GRID      *\n")
        file.write("! NUMXGRID   = NUMBER OF GRID POINTS IN X DIRECTION (= No. of cells + 1)       *\n")
        file.write("! NUMYGRID   = NUMBER OF GRID POINTS IN Y DIRECTION (= No. of cells + 1)       *\n")
        file.write("! DXOUT      = GRID DISTANCE IN X DIRECTION                                    *\n")
        file.write("! DYOUN      = GRID DISTANCE IN Y DIRECTION                                    *\n")
        file.write("! OUTHEIGHTS = HEIGHT OF LEVELS (UPPER BOUNDARY)                               *\n")
        file.write("!*******************************************************************************\n")
        file.write("&OUTGRID\n")
        file.write(" OUTLON0="+" "*(18-8-len(xml.find("longitude/min").text))+xml.find("longitude/min").text+",\n")
        file.write(" OUTLAT0="+" "*(18-8-len(xml.find("latitude/min").text))+xml.find("latitude/min").text+",\n")
        file.write(" NUMXGRID="+" "*(18-9-len(str(Nx)))+str(Nx)+",\n")
        file.write(" NUMYGRID="+" "*(18-9-len(str(Ny)))+str(Ny)+",\n")
        file.write(" DXOUT="+" "*(18-6-len(xml.find("resolution").text))+xml.find("resolution").text+",\n")
        file.write(" DYOUT="+" "*(18-6-len(xml.find("resolution").text))+xml.find("resolution").text+",\n")
        file.write(" OUTHEIGHTS= "+", ".join(height_levels)+",\n")
        file.write(" /\n")
        
def write_receptors_file(config_xml_filepath: str, working_dir: str) -> None:
    LOGGER.info("Preparing RECEPTORS file for FLEXPART")
    xml  = ET.parse(config_xml_filepath)
    xml  = xml.getroot().find("actris/flexpart/receptor")
    with open(working_dir+"/options/RECEPTORS","w") as file:
        for node in xml:
            file.write("&RECEPTORS\n")
            file.write(" RECEPTOR=\""+node.attrib["name"]+"\",\n")
            file.write(" LON="+node.attrib["longitude"]+",\n")
            file.write(" LAT="+node.attrib["latitude"]+",\n")
            file.write(" /\n")

def write_par_mod_file(config_xml_filepath: str, working_dir: str, max_number_parts: int) -> str:
    LOGGER.info("Preparing par_mod.f90 file for FLEXPART")
    xml          = ET.parse(config_xml_filepath)
    xml          = xml.getroot().find("actris/flexpart/par_mod_parameters")
    xml_keys = {"pi":3.14159265,
                "r_earth":6.371e6,
                "r_air":287.05,
                "nxmaxn":0,
                "nymaxn":0,
                "nxmax":361,
                "nymax":181,
                "nuvzmax":138,
                "nwzmax":138,
                "nzmax":138,
                "maxwf":50000,
                "maxtable":1000,
                "numclass":13,
                "ni":11,
                "maxcolumn":3000,
                "maxrand":1000000,
                "maxpart":max_number_parts}
    keys_values = {}
    for key in xml_keys:
        if (xml.find(key) is not None) and (xml.find(key).text!=""):
            value = float(xml.find(key).text) if "." in xml.find(key).text else int(xml.find(key).text)
            keys_values.update({key.upper(): value}) 
        else:
            keys_values.update({key.upper(): xml_keys[key]})

    with open(f"{working_dir}/flexpart_src/par_mod.f90", "w") as file:
        file.write(f"module par_mod\n")
        file.write(f"  implicit none\n")
        file.write(f"  integer,parameter :: dp=selected_real_kind(P=15)\n")
        file.write(f"  integer,parameter :: sp=selected_real_kind(6)\n")
        file.write(f"  integer,parameter :: dep_prec=sp\n")
        file.write(f"  logical, parameter :: lusekerneloutput=.true.\n")
        file.write(f"  logical, parameter :: lparticlecountoutput=.false.\n")
        file.write(f"  integer,parameter :: numpath=4\n")
        file.write(f"  real,parameter :: pi={xml_keys['pi']}, r_earth={xml_keys['r_earth']}, r_air={xml_keys['r_air']}, ga=9.81\n")
        file.write(f"  real,parameter :: cpa=1004.6, kappa=0.286, pi180=pi/180., vonkarman=0.4\n")
        file.write(f"  real,parameter :: rgas=8.31447 \n")
        file.write(f"  real,parameter :: r_water=461.495\n")
        file.write(f"  real,parameter :: karman=0.40, href=15., convke=2.0\n")
        file.write(f"  real,parameter :: hmixmin=100., hmixmax=4500. !, turbmesoscale=0.16\n")
        file.write(f"  real :: d_trop=50., d_strat=0.1, turbmesoscale=0.16 ! turbulence factors can change for different runs\n")
        file.write(f"  real,parameter :: rho_water=1000. !ZHG 2015 [kg/m3]\n")
        file.write(f"  real,parameter :: incloud_ratio=6.2\n")
        file.write(f"  real,parameter :: xmwml=18.016/28.960\n")
        file.write(f"  real,parameter :: ozonescale=60., pvcrit=2.0\n")
        file.write(f"  integer,parameter :: idiffnorm=10800, idiffmax=2*idiffnorm, minstep=1\n")
        file.write(f"  real,parameter :: switchnorth=75., switchsouth=-75.\n")
        file.write(f"  integer,parameter :: nxmax={xml_keys['nxmax']},nymax={xml_keys['nymax']},nuvzmax={xml_keys['nuvzmax']},nwzmax={xml_keys['nwzmax']},nzmax={xml_keys['nzmax']}\n")
        file.write(f"  integer :: nxshift=0 ! shift not fixed for the executable \n")
        file.write(f"  integer,parameter :: maxnests=0,nxmaxn=0,nymaxn=0\n")
        file.write(f"  integer,parameter :: nconvlevmax = nuvzmax-1\n")
        file.write(f"  integer,parameter :: na = nconvlevmax+1\n")
        file.write(f"  integer,parameter :: jpack=4*nxmax*nymax, jpunp=4*jpack\n")
        file.write(f"  integer,parameter :: maxageclass=1,nclassunc=1\n")
        file.write(f"  integer,parameter :: maxreceptor=20\n")
        file.write(f"  integer,parameter :: maxpart={xml_keys['maxpart']}\n")
        file.write(f"  integer,parameter :: maxspec=1\n")
        file.write(f"  real,parameter :: minmass=0.0001\n")
        file.write(f"  integer,parameter :: maxwf={xml_keys['maxwf']}, maxtable={xml_keys['maxtable']}, numclass={xml_keys['numclass']}, ni={xml_keys['ni']}\n")
        file.write(f"  integer,parameter :: numwfmem=2\n")
        file.write(f"  integer,parameter :: maxxOH=72, maxyOH=46, maxzOH=7\n")
        file.write(f"  integer,parameter :: maxcolumn={xml_keys['maxcolumn']}\n")
        file.write(f"  integer,parameter :: maxrand={xml_keys['maxrand']}\n")
        file.write(f"  integer,parameter :: ncluster=5\n")
        file.write(f"  integer,parameter :: unitpath=1, unitcommand=1, unitageclasses=1, unitgrid=1\n")
        file.write(f"  integer,parameter :: unitavailab=1, unitreleases=88, unitpartout=93, unitpartout_average=105\n")
        file.write(f"  integer,parameter :: unitpartin=93, unitflux=98, unitouttraj=96\n")
        file.write(f"  integer,parameter :: unitvert=1, unitoro=1, unitpoin=1, unitreceptor=1\n")
        file.write(f"  integer,parameter :: unitoutgrid=97, unitoutgridppt=99, unitoutinfo=1\n")
        file.write(f"  integer,parameter :: unitspecies=1, unitoutrecept=91, unitoutreceptppt=92\n")
        file.write(f"  integer,parameter :: unitlsm=1, unitsurfdata=1, unitland=1, unitwesely=1\n")
        file.write(f"  integer,parameter :: unitOH=1\n")
        file.write(f"  integer,parameter :: unitdates=94, unitheader=90,unitheader_txt=100, unitshortpart=95, unitprecip=101\n")
        file.write(f"  integer,parameter :: unitboundcond=89\n")
        file.write(f"  integer,parameter :: unittmp=101\n")
        file.write(f"  integer,parameter :: unitoutfactor=102\n")
        file.write(f"  integer,parameter ::  icmv=-9999\n")
        file.write(f"end module par_mod")

def write_ageclasses_file(config_xml_filepath: str, working_dir: str):
    xml             = ET.parse(config_xml_filepath)
    ageclasses_flag = int(xml.getroot().find("actris/flexpart/command/lAgeSpectra").text)
    if ageclasses_flag==0:
        return
    elif ageclasses_flag==1:
        file = open(f"{working_dir}/options/AGECLASSES", "w")
        file.write("************************************************\n")
        file.write("*                                              *\n")
        file.write("*Lagrangian particle dispersion model FLEXPART *\n")
        file.write("*         Please select your options           *\n")
        file.write("*                                              *\n")
        file.write("*This file determines the ageclasses to be used*\n")
        file.write("*                                              *\n")
        file.write("*Ages are given in seconds. The first class    *\n")
        file.write("*starts at age zero and goes up to the first   *\n")
        file.write("*age specified. The last age gives the maximum *\n")
        file.write("*time a particle is carried in the simulation. *\n")
        file.write("*                                              *\n")
        file.write("************************************************\n")
        ages = []
        for node in xml.getroot().findall("actris/flexpart/ageclass/class"):
            ages.append(int(node.text))
        ages.sort()
        for age in ages:
            file.write("&AGECLASS\n")
            file.write("NAGECLASS= 1,\n")
            file.write(f"LAGE= {age},\n")
            file.write("/\n")
        file.close()
    else:
        return

def write_releases_file(config_xml_filepath: str, working_dir: str) -> int:
    xml = ET.parse(config_xml_filepath)
    # ----------------------------------------------------
    # Prepare RELEASES file
    # ----------------------------------------------------
    file = open(working_dir+"/options/RELEASES","w")
    file.write("***************************************************************************************************************\n")
    file.write("*                                                                                                             *\n")
    file.write("*                                                                                                             *\n")
    file.write("*                                                                                                             *\n")
    file.write("*   Input file for the Lagrangian particle dispersion model FLEXPART                                          *\n")
    file.write("*                        Please select your options                                                           *\n")
    file.write("*                                                                                                             *\n")
    file.write("*                                                                                                             *\n")
    file.write("*                                                                                                             *\n")
    file.write("***************************************************************************************************************\n")
    file.write("&RELEASES_CTRL\n")
    file.write(" NSPEC      =           1, ! Total number of species\n")
    file.write(" SPECNUM_REL=          "+xml.getroot().find("actris/flexpart/releases/species").text+", ! Species numbers in directory SPECIES\n")
    file.write(" /\n")
    # ----------------------------------------------------
    release_node        = xml.getroot().find("actris/flexpart/releases")
    total_number_parts  = 0
    for release in release_node:
        if release.tag=="release":
            end_date = datetime.datetime.strptime(release.find('start_date').text+'T'+release.find('start_time').text, '%Y%m%dT%H%M%S') + \
                        datetime.timedelta(days=int(release.find('end_time').text[:2]),
                                           hours=int(release.find('end_time').text[2:4]),
                                           minutes=int(release.find('end_time').text[4:6]),
                                           seconds=float(release.find('end_time').text[6:]))
            file.write("&RELEASE\n")
            file.write(f" IDATE1 = {release.find('start_date').text},\n")
            file.write(f" ITIME1 = {release.find('start_time').text},\n")
            file.write(f" IDATE2 = {datetime.datetime.strftime(end_date, '%Y%m%d')},\n")
            file.write(f" ITIME2 = {datetime.datetime.strftime(end_date, '%H%M%S')},\n")
            file.write(f" LON1 = {release.find('zones/zone/lonmin').text},\n")
            file.write(f" LON2 = {release.find('zones/zone/lonmax').text},\n")
            file.write(f" LAT1 = {release.find('zones/zone/latmin').text},\n")
            file.write(f" LAT2 = {release.find('zones/zone/latmax').text},\n")
            file.write(f" Z1 = {release.find('altitude_min').text},\n")
            file.write(f" Z2 = {release.find('altitude_max').text},\n")
            file.write(" ZKIND = 1,\n")
            file.write(f" MASS = 1.000000E+00,\n")
            file.write(f" PARTS = 100000,\n")
            file.write(f" COMMENT = \"{release.attrib['name']}\",\n")
            file.write(" /\n")
            total_number_parts = total_number_parts + 100000
    file.close()
    return total_number_parts

def compile_flexpart(working_dir: str) -> None:
    # Compile FLEXPART
    LOGGER.info("Compiling FLEXPART")
    bashCommand = ["make", "clean"]
    result = subprocess.run(bashCommand, cwd=f"{working_dir}/flexpart_src", capture_output=True)
    if result.returncode!=0:
        LOGGER.error(result.stderr)
        return 1
    bashCommand = ["make", "ncf=yes"]
    result = subprocess.run(bashCommand, cwd=f"{working_dir}/flexpart_src", capture_output=True)
    if result.returncode!=0:
        LOGGER.error(result.stderr)
        return 1
    # Copy the executable into the working dir
    bashCommand = ["cp", f"{working_dir}/flexpart_src/FLEXPART", f"{working_dir}/"]
    result = subprocess.run(bashCommand, capture_output=True)
    if result.returncode!=0:
        LOGGER.error(result.stderr)
        return 1
    return 0

def check_ECMWF_pool(config_xml_filepath: str, working_dir: str) -> int:
    exit_flag = 0
    LOGGER.info("Checking ECMWF pool for the available files")
    ecmwf_pool = get_ECMWF_pool_path(config_xml_filepath)
    with open(working_dir+"/AVAILABLE","r") as file:
        lines = file.readlines()
    list_EN_files = [line.split(" ")[7] for line in lines[3:]]
    for file in list_EN_files:
        if os.path.exists(ecmwf_pool+"/"+file):
            LOGGER.info(file+" exists")
        else:
            LOGGER.error(file+" does not exist")
            exit_flag = 1
    return exit_flag

def get_working_dir(config_xml_filepath: str) -> str:
    xml          = ET.parse(config_xml_filepath)
    return xml.getroot().find("actris/paths/working_dir").text

def copy_source_files(working_dir: str) -> None:
    local_src_dir = f"{working_dir}/flexpart_src/"
    if not os.path.exists(local_src_dir):
        os.mkdir(local_src_dir)
    bashCommand = [f"cp -r {FLEXPART_ROOT}/src/* {local_src_dir}"]
    result = subprocess.run(bashCommand, capture_output=True, shell=True)
    if result.returncode!=0:
        LOGGER.error(result.stderr)
        return 1
    return 0

def prepare_working_dir(working_dir: str) -> None:
    if not os.path.exists(working_dir):
        try:
            os.mkdir(f"{working_dir}")
        except e:
            LOGGER.error(e)
            return 1
    if not os.path.exists(f"{working_dir}/options"):
        os.mkdir(f"{working_dir}/options")
    if not os.path.exists(f"{working_dir}/output"):
        os.mkdir(f"{working_dir}/output")
    shutil.copy(f"{FLEXPART_ROOT}/options/IGBP_int1.dat", f"{working_dir}/options/")
    shutil.copy(f"{FLEXPART_ROOT}/options/surfdata.t", f"{working_dir}/options/")
    shutil.copy(f"{FLEXPART_ROOT}/options/surfdepo.t", f"{working_dir}/options/")
    if not os.path.exists(f"{working_dir}/options/SPECIES/"):
        shutil.copytree(f"{FLEXPART_ROOT}/options/SPECIES", f"{working_dir}/options/SPECIES/")
    return 0

def run_bash_command(command_string: str, working_dir: str) -> None:
    """
    Executes bash commands and logs its output simultaneously

    Args:
        command_string (str): bash command to execute
    """
    process = subprocess.Popen(command_string, cwd=working_dir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while True:
        output = process.stdout.readline()
        if process.poll() is not None:
            break
        if output:
            LOGGER.info(output.strip().decode('utf-8'))
    return_code = process.poll()
    return return_code


# ===============================================================================================================


if __name__=="__main__":

    import argparse
    
    parser = argparse.ArgumentParser(description="Python code that prepare all FLEXPART inputs"
                                    "and launch FLEXPART simulations based on your configuration.xml and "
                                    "parameters.xml files where you configure your simulation time, input data etc", 
                                    formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--config", type=str, default="./actris-config.xml",
                        help="Filepath to your configuration xml file.")
    parser.add_argument("--shell-log",help="Display log also in the shell",action="store_true")

    args = parser.parse_args()

    config_xmlpath = args.config
    wdir           = get_working_dir(config_xmlpath)
    status         = prepare_working_dir(wdir)

    global LOGGER, LOG_FILEPATH
    LOG_FILEPATH = wdir+"/actris_"+datetime.datetime.now().strftime("%Y%m%d_%H%M%S")+".log"
    LOGGER = start_log(args.shell_log, LOG_FILEPATH)
    if args.shell_log==True:
        print_header_in_terminal()
    else:
        write_header_in_file(LOG_FILEPATH)

    if status!=0:
        LOGGER.error("Something went wrong...")
        sys.exit(1)

    ##########################################################################

    verif_xml_file(config_xmlpath)

    ##########################################################################

    write_available_file(config_xmlpath,wdir)
    status = check_ECMWF_pool(config_xmlpath,wdir)
    if status!=0:
        LOGGER.error("Some of the ECMWF files are not available in your indicated directory, please check your data and configuration file and retry again.")
        sys.exit(1)
    
    write_pathnames_file(config_xmlpath,wdir)
    write_command_file(config_xmlpath,wdir)
    write_outgrid_file(config_xmlpath,wdir)
    write_receptors_file(config_xmlpath,wdir)
    Nparts = write_releases_file(config_xmlpath,wdir)
    write_ageclasses_file(config_xmlpath,wdir)

    status = copy_source_files(wdir)
    if status==1:
        LOGGER.error("Something went wrong...")
        sys.exit(1)

    write_par_mod_file(config_xmlpath,wdir,Nparts)

    status = compile_flexpart(wdir)
    if status!=0:
        LOGGER.error("Something went wrong...")
        sys.exit(1)
    
    LOGGER.info("Launching FLEXPART")

    run_bash_command("./FLEXPART", wdir)

    # output_netcdf = glob.glob(f"{wdir}/output/*.nc")[0]
