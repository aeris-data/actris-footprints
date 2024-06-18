#!/bin/bash

# Get script filename and filepath
SCRIPT_PATH=$0
SCRIPT_NAME=$(basename ${SCRIPT_PATH})

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#                                                                                                           #
#    ██████  ██████  ███    ██ ███████ ██  ██████  ██    ██ ██████   █████  ████████ ██  ██████  ███    ██  #
#   ██      ██    ██ ████   ██ ██      ██ ██       ██    ██ ██   ██ ██   ██    ██    ██ ██    ██ ████   ██  #
#   ██      ██    ██ ██ ██  ██ █████   ██ ██   ███ ██    ██ ██████  ███████    ██    ██ ██    ██ ██ ██  ██  #
#   ██      ██    ██ ██  ██ ██ ██      ██ ██    ██ ██    ██ ██   ██ ██   ██    ██    ██ ██    ██ ██  ██ ██  #
#    ██████  ██████  ██   ████ ██      ██  ██████   ██████  ██   ██ ██   ██    ██    ██  ██████  ██   ████  #
#                                                                                                           #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# Configuration that allows to use "module load" command on NUWA
. /etc/profile.d/modules.sh
export MODULEPATH=/home/sila/modules/compilers:/home/sila/modules/libraries/generic
export MODULECONFIGFILE=/home/sila/modules/config/modulerc

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#                                                                                   #
#     ███████ ██    ██ ███    ██  ██████ ████████ ██  ██████  ███    ██ ███████     #
#     ██      ██    ██ ████   ██ ██         ██    ██ ██    ██ ████   ██ ██          #
#     █████   ██    ██ ██ ██  ██ ██         ██    ██ ██    ██ ██ ██  ██ ███████     #
#     ██      ██    ██ ██  ██ ██ ██         ██    ██ ██    ██ ██  ██ ██      ██     #
#     ██       ██████  ██   ████  ██████    ██    ██  ██████  ██   ████ ███████     #
#                                                                                   #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

function help() {
    bold=$(tput bold)
    normal=$(tput sgr0)
    echo ""
    echo "###                 |    *"
    echo "###                 |  *"
    echo "###                 | *"
    echo "###             ,,gg|dY\"\"\"\"Ybbgg,,"
    echo "###        ,agd\"\"'  |           \`\"\"bg,"
    echo "###     ,gdP\"     A C T R I S       \"Ybg,"
    echo "###                     FRANCE"
    echo "###"
    echo "### This script is intended for FLEXPART simulation, SOFT-io CO contribution computation and creation of the CO receptor-"
    echo "### -source footprints for an ACTRIS station. Simulation will be performed in the backward mode to the J-10 days time limit. The"
    echo "### user should just select the station, the date/time of the simulation, from which the J-10 period will be counted, and"
    echo "### provide the configuration file where paths to working and output directories are indicated. Options --flexpart, --softio and"
    echo "### --footprint allow to activate one or multiple processings."
    echo "###"
    echo "### Usage : ${bold}${SCRIPT_NAME} [options] arguments${normal}"
    echo "###"
    echo "### Options:"
    echo "###   ${bold}-h|--help${normal}        Show this help message and exit"
    echo "###   ${bold}--flexpart${normal}       Activate FLEXPART simulation"
    echo "###   ${bold}--softio${normal}         Activate SOFT-io computations"
    echo "###   ${bold}--footprints${normal}     Activate creation of the footprint image"
    echo "###"
    echo "### Arguments:"
    echo "###   ${bold}-n        station_name_code${normal}   ID code (short_name) of one of the stations from your configuration file"                                   
    echo "###   ${bold}-d        YYYYMMDDHH${normal}          date and time of the simulation"
    echo "###   ${bold}-c,--conf configuration.file${normal}  configuration file with paths"
    echo "###"
    echo "### Configuration file is an ASCII file containing paths to source codes and workingd/data directories. The syntaxe is as follows :"
    echo "###    SRC_DIR=\"/path/to/folder/with/python/source/codes\""
    echo "###    DATA_DIR=\"/path/to/folder/with/ecmwf/grib/data\""
    echo "###    SINGULARITY_FILEPATH=\"/path/to/the/singularity/image.sif\""
    echo "###    ROOT_WDIR=\"/path/to/root/working/folder/for/subfolders\""
    echo "###    FLEXPART_OUT_DIR=\"/path/to/folder/for/flexpart/output\""
    echo "###    SOFTIO_OUT_DIR=\"/path/to/folder/for/softio/output\""
    echo "###    SOFTIO_DATABASE=\"/path/to/output/softio/database.nc\""
    echo "###    FOOTPRINTS_DATABASE=\"/path/to/output/footprints/images/database.zarr\""
    echo "###    STATIONS_CONF=\"/path/to/file/with/stations/configuration.json\""
    echo "###"
    echo "### Stations configuration file is a JSON file with syntaxe as follows :"
    echo "###    ["
    echo "###       {"
    echo "###           \"short_name\":\"PUY\","
    echo "###           \"long_name\":\"Puy de Dôme\","
    echo "###           \"longitude\":2.964886,"
    echo "###           \"latitude\":45.772223,"
    echo "###           \"altitude\":1465,"
    echo "###           \"release_heights\":\"500 1500\""
    echo "###       },"
    echo "###       {...},"
    echo "###       {...}"
    echo "###    ]"
    echo "###"
    echo "### Example :"
    echo "###   ${bold}${SCRIPT_NAME} -n 'SAC' -d 2022050600 -conf may_paths.conf --flexpart --softio --footprint${normal} will launch a"
    echo "### simulation for the SIRTA station starting on 06/05/2022 at 00h and going backward up to 26/04/2022 00h; then launch SOFT-io"
    echo "### and create footprints image."
    echo "###   ${bold}${SCRIPT_NAME} -n 'SAC' -d 2022050600 -conf may_paths.conf --flexpart${normal} will launch the same simulation as"
    echo "### described above, but without SOFT-io nor footprints image creation"
    echo ""
}

function info() {
    msg=$1
    line_number=${BASH_LINENO[0]}
    calling_func=${FUNCNAME[1]}
    echo "$(date +'%d/%m/%Y %H:%M:%S') - [INFO]    (${calling_func}:${line_number}) ${msg}"
}
function error() {
    msg=$1
    line_number=${BASH_LINENO[0]}
    calling_func=${FUNCNAME[1]}
    echo "$(date +'%d/%m/%Y %H:%M:%S') - [ERROR]   (${calling_func}:${line_number}) ${msg}"
}
function warning() {
    msg=$1
    line_number=${BASH_LINENO[0]}
    calling_func=${FUNCNAME[1]}
    echo "$(date +'%d/%m/%Y %H:%M:%S') - [WARNING] (${calling_func}:${line_number}) ${msg}"
}

function check_args(){
    status=0
    if [ -z ${STATION_CODE} ]; then
        error "Station code argument is mandatory, please verify your arguments and launch again"
        status=1
    fi
    if [ -z ${START_DATE} ]; then
        error "Start date argument is mandatory, please verify your arguments and launch again"
        status=1
    fi
    if [ -z ${CONFIG_FILE} ]; then
        error "Configuration file is mandatory, please verify your arguments and launch again"
        status=
    fi
    if [[ ${FLEXPART_FLAG} == 0 ]] && [[ ${SOFTIO_FLAG} == 0 ]] && [[ ${FOOTPRINTS_FLAG} == 0 ]]; then
        warning "None of the processing were chosen (FLEXPART, SOFT-io, footprints image), exiting from the script"
        status=1
    fi
    if [ ${status} == 1 ]; then exit 1; fi
}

function check_station_id(){
    ids=($(cat ${STATIONS_CONF} | jq '.[].short_name'))
    index=-1
    for ii in "${!ids[@]}"; do
        ids[${ii}]=${ids[${ii}]//\"/""}
        if [[ "${ids[${ii}]}" == "${STATION_CODE}" ]]; then
            index=${ii}
            break
        fi
    done
    if [ "${index}" == -1 ]; then
        return 1
    else
        return 0
    fi
}

function check_config(){
    status=0
    # **************************************************************************************************
    # Check if all of the arguments are present
    if [ -z ${SRC_DIR} ]; then error "SRC_DIR argument is mandatory, please verify your configuration file and try again"; status=1; fi
    if [ -z ${DATA_DIR} ]; then error "DATA_DIR argument is mandatory, please verify your configuration file and try again"; status=1; fi
    if [ -z ${SINGULARITY_FILEPATH} ]; then error "SINGULARITY_FILEPATH argument is mandatory, please verify your configuration file and try again"; status=1; fi
    if [ -z ${ROOT_WDIR} ]; then error "ROOT_WDIR argument is mandatory, please verify your configuration file and try again"; status=1; fi
    if [ -z ${FLEXPART_OUT_DIR} ]; then error "FLEXPART_OUT_DIR argument is mandatory, please verify your configuration file and try again"; status=1; fi
    if [ -z ${SOFTIO_OUT_DIR} ]; then error "SOFTIO_OUT_DIR argument is mandatory, please verify your configuration file and try again"; status=1; fi
    if [ -z ${SOFTIO_DATABASE} ]; then error "SOFTIO_DATABASE argument is mandatory, please verify your configuration file and try again"; status=1; fi
    if [ -z ${FOOTPRINTS_DATABASE} ]; then error "FOOTPRINTS_DATABASE argument is mandatory, please verify your configuration file and try again"; status=1; fi
    if [ -z ${STATIONS_CONF} ]; then error "STATIONS_CONF argument is mandatory, please verify your configuration file and try again"; status=1; fi
    if [ ${status} == 1 ]; then exit 1; fi
    # **************************************************************************************************
    # Check if the given station code is present in the configuration file
    if ! check_station_id; then
        warning "Provided station id was not found in the stations configuration file ${STATIONS_CONF}, please check your arguments and try again"
        exit 1
    fi
    get_station_info
    # **************************************************************************************************
    # Not ok if these do not exist since these are input files/directories
    if [ ! -d ${SRC_DIR} ]; then
        error "SRC_DIR ${SRC_DIR} does not exist, verify your configuration file and try again"
        status=1
    fi
    if [ ! -d ${DATA_DIR} ]; then
        error "DATA_DIR ${DATA_DIR} does not exist, verify your configuration file and launch again"
        status=1
    fi
    if [ ! -f ${SINGULARITY_FILEPATH} ] && [ ! -d ${SINGULARITY_FILEPATH} ]; then
        error "SINGULARITY_FILEPATH ${SINGULARITY_FILEPATH} does not exist, verify your configuration file and launch again"
        status=1
    fi
    if [ ${status} == 1 ]; then exit 1; fi
    # **************************************************************************************************
    # These files/directories are output files/directories so they will be created if do not exist
    if [ ! -d ${ROOT_WDIR} ]; then
        warning "ROOT_WDIR does not exist, it will be created if permissions allow it"
        info "Creating ${ROOT_WDIR} as ROOT_WDIR..."
        mkdir -p ${ROOT_WDIR}
    fi
    station_working_dir="${ROOT_WDIR}/${_station_id}"
    if [ ! -d ${station_working_dir} ]; then 
        info "Creating ${station_working_dir} as station working directory..."
        mkdir -p ${station_working_dir}
    fi

    if [ ! -d ${FLEXPART_OUT_DIR} ]; then
        warning "FLEXPART_OUT_DIR does not exist, it will be created if permissions allow it"
        info "Creating ${FLEXPART_OUT_DIR} as FLEXPART_OUT_DIR..."
        mkdir -p ${FLEXPART_OUT_DIR}
    fi

    if [ ! -d ${SOFTIO_OUT_DIR} ]; then
        warning "SOFTIO_OUT_DIR does not exist, it will be created if permissions allow it"
        info "Creating ${SOFTIO_OUT_DIR} as SOFTIO_OUT_DIR..."
        mkdir -p ${SOFTIO_OUT_DIR}
    fi

    info "Station working directory     : ${station_working_dir}"
    if [ ${FLEXPART_FLAG} == 1 ]; then info "Directory for FLEXPART output : ${FLEXPART_OUT_DIR}"; fi
    if [ ${SOFTIO_FLAG} == 1 ]; then
        info "Directory for SOFT-io output  : ${SOFTIO_OUT_DIR}"
        info "SOFT-io database              : ${SOFTIO_DATABASE}"
    fi
    if [ ${FOOTPRINTS_FLAG} == 1 ]; then info "Footprints image database     : ${FOOTPRINTS_DATABASE}"; fi
}

function perform_flexpart_simulation(){

    echo "+---------------------------------------------------------------------------------------------------------------------------+"
    echo "|     ⣄⠇⠁       ⠠⠎  ⠈⠑⣄                       ⢀ ⣴⠋                                                                          |"
    echo "|    ⠂⠋               ⠠⠟⠕⠦⡀                ⠤⢆⡋⠰⠸⠗                                                                           |"
    echo "|   ⡁                    ⢡⠇               ⢼⣱⠁    ⢀⢠⠏⠒                                                                       |"
    echo "|   ⠁⠐⠐⠄    ⢀         ⣀⡀⠖⠛            ⠠⠰⠺⡁⡛⠁    ⣜       ███████╗██╗     ███████╗██╗  ██╗██████╗  █████╗ ██████╗ ████████╗   |"
    echo "|      ⠙⠁⠄⠆⡸⠓⡆⠠  ⢀⡞⠤⠠⠐⠁           ⣀⠐⡷⡾⡃⠉     ⢠⠰⠰⢇⠨⠦⡵    ██╔════╝██║     ██╔════╝╚██╗██╔╝██╔══██╗██╔══██╗██╔══██╗╚══██╔══╝   |"
    echo "|             ⠈⠉ ⠁              ⣴⠋⠉ ⠉⠟    ⣄⡃⠉      ⠁    █████╗  ██║     █████╗   ╚███╔╝ ██████╔╝███████║██████╔╝   ██║      |"
    echo "|      ⡀ ⡀⡀                   ⠠⢅⠃        ⣠⠃             ██╔══╝  ██║     ██╔══╝   ██╔██╗ ██╔═══╝ ██╔══██║██╔══██╗   ██║      |"
    echo "|   ⡀⡵⠁⠁⠉⠘⠁⢢⣰ ⠄                ⠽⣯⡀                      ██║     ███████╗███████╗██╔╝ ██╗██║     ██║  ██║██║  ██║   ██║      |"
    echo "|   ⠁        ⠉⣥⡕⢀ ⡀⢀            ⠪⡯                      ╚═╝     ╚══════╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝      |"
    echo "|              ⠊⡟⠭⠊⠊⠉⠓⠥⠰⡀       ⠐⡅                                                                                          |"
    echo "|   ⡄⡀                 ⠉⢯⠄  ⡀    ⠉⣦⠄⠠⠠⠠⠂                                                                                    |"
    echo "|   ⠉⠋⠻⢖⣤⢥⡦⣤⠷⣀⢄⡀      ⣰⡽⠃⠈⠁⠙⠁⣅⡠      ⠁⠈                                                                                     |"
    echo "+---------------------------------------------------------------------------------------------------------------------------+"

    info "Getting FLEXPART simulation parameters..."
    date=${START_DATE:0:8}
    hour=${START_DATE:8:2}
    simu_start_date=$(date -d "${date} - 10 days" "+%Y%m%d")
    simu_end_date=${date}
    simu_start_time=${hour}0000
    simu_end_time=${hour}0000
    release_start_date=$(date -d "@$(($(date -d "${simu_end_date} ${hour}:00:00" +"%s") - 3600))" +"%Y%m%d")
    release_start_time=$(date -d "@$(($(date -d "${simu_end_date} ${hour}:00:00" +"%s") - 3600))" +"%H%M")00
    lat_min=$(echo "${_station_lat} - 0.25" | bc)
    lat_max=$(echo "${_station_lat} + 0.25" | bc)
    lon_min=$(echo "${_station_lon} - 0.25" | bc)
    lon_max=$(echo "${_station_lon} + 0.25" | bc)
    for alt_value in ${_station_alts}; do
        wdir="${station_working_dir}/wdir-${date}${hour}-${alt_value}"
        if [ ! -d ${wdir} ]; then mkdir -p ${wdir}; fi
        alt_min=${alt_value}
        alt_max=$((alt_min + 50))
        simulation_config_file=${wdir}/actris-config.xml
        cat <<EOF > ${simulation_config_file}
<?xml version="1.0" encoding="UTF-8"?>
<config>
    <actris>
        <version>7.0</version>
        <simulation_start>
            <date>${simu_start_date}</date>
            <time>${simu_start_time}</time>
        </simulation_start>
        <simulation_end>
            <date>${simu_end_date}</date>
            <time>${simu_end_time}</time>
        </simulation_end>
        <ecmwf_time>
            <dtime>3</dtime>
        </ecmwf_time>
        <flexpart>
            <root>/usr/local/flexpart_v10.4_3d7eebf/</root>
            <par_mod_parameters>
                <nxmax>360</nxmax>
                <nymax>181</nymax>
                <nuvzmax>138</nuvzmax>
                <nwzmax>138</nwzmax>
                <nzmax>138</nzmax>
            </par_mod_parameters>
            <outGrid>
                <longitude>
                    <min>-179</min>
                    <max>181</max>
                </longitude>
                <latitude>
                    <min>-90</min>
                    <max>90</max>
                </latitude>
                <resolution>1</resolution>
                <height>
                    <level>1000.0</level>
                    <level>2000.0</level>
                    <level>3000.0</level>
                    <level>4000.0</level>
                    <level>5000.0</level>
                    <level>6000.0</level>
                    <level>7000.0</level>
                    <level>8000.0</level>
                    <level>9000.0</level>
                    <level>10000.0</level>
                    <level>11000.0</level>
                    <level>50000.0</level>
                </height>
            </outGrid>
            <command>
                <forward>-1</forward>
                <time>
                    <output>10800</output>
                </time>
                <iOut>9</iOut>
            </command>
            <releases>
                <species>24</species>
                <release name='Release1'>
                    <start_date>${release_start_date}</start_date>
                    <start_time>${release_start_time}</start_time>
                    <duration>00000000</duration>
                    <altitude_min>${alt_min}</altitude_min>
                    <altitude_max>${alt_max}</altitude_max>
                    <zones>
                        <zone name='${_station_name}'>
                            <latmin>${lat_min}</latmin>
                            <latmax>${lat_max}</latmax>
                            <lonmin>${lon_min}</lonmin>
                            <lonmax>${lon_max}</lonmax>
                        </zone>
                    </zones>
                </release>
            </releases>
        </flexpart>
        <paths>
            <working_dir>${wdir}</working_dir>
            <ecmwf_dir>${DATA_DIR}</ecmwf_dir>
        </paths>
    </actris>
</config>
EOF
        # exit 0
        module load singularity/3.10.2
        # +----------------------------------+
        # | Launch simulation                |
        # +----------------------------------+
        flexpart_output_file="${FLEXPART_OUT_DIR}/${_station_id}-${date}${hour}-${simu_start_date}-${alt_value}.nc"
        singularity exec --bind ${DATA_DIR},${ROOT_WDIR} \
            ${SINGULARITY_FILEPATH} \
            /usr/local/py_envs/actris_env/bin/python ${SRC_DIR}/actris.py \
            --config ${simulation_config_file}
        _flexpart_native_output_file=$(find ${wdir}/output -iname "grid_time*.nc")
        if [ -f ${_flexpart_native_output_file} ]; then
            mv ${_flexpart_native_output_file} ${flexpart_output_file}
        else
            error "Something went wrong with FLEXPART simulation..."
        fi
    done
}

function apply_softio(){

    echo "+-----------------------------------------------------------------------------------------------------------+"
    echo "|     ⣄⠇⠁       ⠠⠎  ⠈⠑⣄                       ⢀ ⣴⠋                                                          |"
    echo "|    ⠂⠋               ⠠⠟⠕⠦⡀                ⠤⢆⡋⠰⠸⠗                                                           |"
    echo "|   ⡁                    ⢡⠇               ⢼⣱⠁    ⢀⢠⠏⠒                                                       |"
    echo "|   ⠁⠐⠐⠄    ⢀         ⣀⡀⠖⠛            ⠠⠰⠺⡁⡛⠁    ⣜       ███████╗ ██████╗ ███████╗████████╗   ██╗ ██████╗    |"
    echo "|      ⠙⠁⠄⠆⡸⠓⡆⠠  ⢀⡞⠤⠠⠐⠁           ⣀⠐⡷⡾⡃⠉     ⢠⠰⠰⢇⠨⠦⡵    ██╔════╝██╔═══██╗██╔════╝╚══██╔══╝   ██║██╔═══██╗   |"
    echo "|             ⠈⠉ ⠁              ⣴⠋⠉ ⠉⠟    ⣄⡃⠉      ⠁    ███████╗██║   ██║█████╗     ██║█████╗██║██║   ██║   |"
    echo "|      ⡀ ⡀⡀                   ⠠⢅⠃        ⣠⠃             ╚════██║██║   ██║██╔══╝     ██║╚════╝██║██║   ██║   |"
    echo "|   ⡀⡵⠁⠁⠉⠘⠁⢢⣰ ⠄                ⠽⣯⡀                      ███████║╚██████╔╝██║        ██║      ██║╚██████╔╝   |"
    echo "|   ⠁        ⠉⣥⡕⢀ ⡀⢀            ⠪⡯                      ╚══════╝ ╚═════╝ ╚═╝        ╚═╝      ╚═╝ ╚═════╝    |"
    echo "|              ⠊⡟⠭⠊⠊⠉⠓⠥⠰⡀       ⠐⡅                                                                          |"
    echo "|   ⡄⡀                 ⠉⢯⠄  ⡀    ⠉⣦⠄⠠⠠⠠⠂                                                                    |"
    echo "|   ⠉⠋⠻⢖⣤⢥⡦⣤⠷⣀⢄⡀      ⣰⡽⠃⠈⠁⠙⠁⣅⡠      ⠁⠈                                                                     |"
    echo "+-----------------------------------------------------------------------------------------------------------+"

    module load singularity/3.10.2
    files_to_process=($(find ${FLEXPART_OUT_DIR} -iname "${_station_id}-${START_DATE}*.nc"))
    if [ ! -z ${files_to_process} ]; then
        for flexpart_output_file in ${files_to_process[@]}; do
            singularity exec \
                --bind /o3p,/home/wolp/data,${FLEXPART_OUT_DIR},${SOFTIO_OUT_DIR},$(dirname ${SOFTIO_DATABASE}) \
                ${SINGULARITY_FILEPATH} \
                /usr/local/py_envs/softio_env/bin/python ${SRC_DIR}/apply-softio.py \
                -f ${flexpart_output_file} \
                -n ${_station_id} \
                -d ${SOFTIO_OUT_DIR} \
                -o ${SOFTIO_DATABASE}
        done
    else
        warning "No FLEXPART output were found for this configuration to run SOFT-IO computations on it. Verify your configuration and/or FLEXPART output and try again."
        exit 1
    fi
}

function create_footprints_image(){

    echo "+-------------------------------------------------------------------------------------------------------------------------------------------+"
    echo "|     ⣄⠇⠁       ⠠⠎  ⠈⠑⣄                       ⢀ ⣴⠋                                                                                          |"
    echo "|    ⠂⠋               ⠠⠟⠕⠦⡀                ⠤⢆⡋⠰⠸⠗                                                                                           |"
    echo "|   ⡁                    ⢡⠇               ⢼⣱⠁    ⢀⢠⠏⠒                                                                                       |"
    echo "|   ⠁⠐⠐⠄    ⢀         ⣀⡀⠖⠛            ⠠⠰⠺⡁⡛⠁    ⣜       ███████╗ ██████╗  ██████╗ ████████╗██████╗ ██████╗ ██╗███╗   ██╗████████╗███████╗   |"
    echo "|      ⠙⠁⠄⠆⡸⠓⡆⠠  ⢀⡞⠤⠠⠐⠁           ⣀⠐⡷⡾⡃⠉     ⢠⠰⠰⢇⠨⠦⡵    ██╔════╝██╔═══██╗██╔═══██╗╚══██╔══╝██╔══██╗██╔══██╗██║████╗  ██║╚══██╔══╝██╔════╝   |"
    echo "|             ⠈⠉ ⠁              ⣴⠋⠉ ⠉⠟    ⣄⡃⠉      ⠁    █████╗  ██║   ██║██║   ██║   ██║   ██████╔╝██████╔╝██║██╔██╗ ██║   ██║   ███████╗   |"
    echo "|      ⡀ ⡀⡀                   ⠠⢅⠃        ⣠⠃             ██╔══╝  ██║   ██║██║   ██║   ██║   ██╔═══╝ ██╔══██╗██║██║╚██╗██║   ██║   ╚════██║   |"
    echo "|   ⡀⡵⠁⠁⠉⠘⠁⢢⣰ ⠄                ⠽⣯⡀                      ██║     ╚██████╔╝╚██████╔╝   ██║   ██║     ██║  ██║██║██║ ╚████║   ██║   ███████║   |"
    echo "|   ⠁        ⠉⣥⡕⢀ ⡀⢀            ⠪⡯                      ╚═╝      ╚═════╝  ╚═════╝    ╚═╝   ╚═╝     ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝   |"
    echo "|              ⠊⡟⠭⠊⠊⠉⠓⠥⠰⡀       ⠐⡅                                                                                                          |"
    echo "|   ⡄⡀                 ⠉⢯⠄  ⡀    ⠉⣦⠄⠠⠠⠠⠂                                                                                                    |"
    echo "|   ⠉⠋⠻⢖⣤⢥⡦⣤⠷⣀⢄⡀      ⣰⡽⠃⠈⠁⠙⠁⣅⡠      ⠁⠈                                                                                                     |"
    echo "+-------------------------------------------------------------------------------------------------------------------------------------------+"
    
    module load singularity/3.10.2
    files_to_process=($(find ${FLEXPART_OUT_DIR} -iname "${_station_id}-${START_DATE}*.nc"))
    if [ ! -z ${files_to_process} ]; then
        for flexpart_output_file in ${files_to_process[@]}; do
            singularity exec \
                --bind ${FLEXPART_OUT_DIR},$(dirname ${FOOTPRINTS_DATABASE}) \
                ${SINGULARITY_FILEPATH} \
                /usr/local/py_envs/footprints_env/bin/python ${SRC_DIR}/create-footprints.py \
                -f ${flexpart_output_file} \
                -n ${_station_id} \
                -o ${FOOTPRINTS_DATABASE}
        done
    else
        warning "No FLEXPART output were found for this configuration to create footprints images from it. Verify your configuration and/or FLEXPART output and try again."
        exit 1
    fi
}

function get_station_info(){
    ids=($(cat ${STATIONS_CONF} | jq '.[].short_name'))
    index=-1
    for ii in "${!ids[@]}"; do
        # ids[${ii}]=${ids[${ii}]//\"/""}
        if [[ "${ids[${ii}]}" == "\"${STATION_CODE}\"" ]]; then
            index=${ii}
            break
        fi
    done
    _station_id=${STATION_CODE}
    readarray -t arr < <(jq -r '.[].standard_name' "${STATIONS_CONF}")
    _station_name=${arr[${index}]}
    arr=($(cat ${STATIONS_CONF} | jq '.[].latitude'))
    _station_lat=${arr[${index}]}
    arr=($(cat ${STATIONS_CONF} | jq '.[].longitude'))
    _station_lon=${arr[${index}]}
    _station_coords="${_station_lat} ${_station_lon}"
    readarray -t arr < <(jq -r '.[].release_heights' "${STATIONS_CONF}")
    _station_alts=${arr[${index}]}
    # echo "_station_id      : ${_station_id}"
    # echo "_station_name    : ${_station_name}"
    # echo "_station_coords  : ${_station_coords}"
    # echo "_station_alts    : ${_station_alts}"  
}

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#                                                                             #
#                      ███    ███  █████  ██ ███    ██                        #
#                      ████  ████ ██   ██ ██ ████   ██                        #
#                      ██ ████ ██ ███████ ██ ██ ██  ██                        #
#                      ██  ██  ██ ██   ██ ██ ██  ██ ██                        #
#                      ██      ██ ██   ██ ██ ██   ████                        #
#                                                                             #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

function main(){
    if [ ${FLEXPART_FLAG} == 1 ]; then
        perform_flexpart_simulation
    fi
    if [ ${SOFTIO_FLAG} == 1 ]; then
        apply_softio
    fi
    if [ ${FOOTPRINTS_FLAG} == 1 ]; then
        create_footprints_image
    fi
}

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#                                                                             #
#                  ██ ███    ██ ████████ ██████   ██████                      #
#                  ██ ████   ██    ██    ██   ██ ██    ██                     #
#                  ██ ██ ██  ██    ██    ██████  ██    ██                     #
#                  ██ ██  ██ ██    ██    ██   ██ ██    ██                     #
#                  ██ ██   ████    ██    ██   ██  ██████                      #
#                                                                             #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

SOFTIO_FLAG=0
FLEXPART_FLAG=0
FOOTPRINTS_FLAG=0

opts=$(getopt --longoptions "help,conf:,softio,flexpart,footprints" --name "$(basename "$0")" --options "h,n:,d:,c:" -- "$@")
eval set -- "$opts"

while [[ $# -gt 0 ]]; do
    case "$1" in
        -n) shift; STATION_CODE=$1; shift;;
        -d) shift; START_DATE=$1; shift;;
        -c|--conf) shift; CONFIG_FILE=$1; shift;;
        -h|--help) shift; help; exit 0;;
        --softio) shift; SOFTIO_FLAG=1;;
        --flexpart) shift; FLEXPART_FLAG=1;;
        --footprints) shift; FOOTPRINTS_FLAG=1;;
        \?) shift; error "Unrecognized options"; exit 1; shift;;
        --) break;;
    esac
done

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#                                                                                                                                                             #
#                  █████   ██████ ████████ ██████  ██ ███████     ███████ ██ ███    ███ ██    ██ ██       █████  ████████ ██  ██████  ███    ██               #
#                 ██   ██ ██         ██    ██   ██ ██ ██          ██      ██ ████  ████ ██    ██ ██      ██   ██    ██    ██ ██    ██ ████   ██               #
#                 ███████ ██         ██    ██████  ██ ███████     ███████ ██ ██ ████ ██ ██    ██ ██      ███████    ██    ██ ██    ██ ██ ██  ██               #
#                 ██   ██ ██         ██    ██   ██ ██      ██          ██ ██ ██  ██  ██ ██    ██ ██      ██   ██    ██    ██ ██    ██ ██  ██ ██               #
#                 ██   ██  ██████    ██    ██   ██ ██ ███████     ███████ ██ ██      ██  ██████  ███████ ██   ██    ██    ██  ██████  ██   ████               #
#                                                                                                                                                             #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

check_args
source ${CONFIG_FILE}
check_config
main
