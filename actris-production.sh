#!/bin/bash

set -e

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
    echo "$(date +'%d/%m/%Y %H:%M:%S') - [ERROR]    (${calling_func}:${line_number}) ${msg}"
}

function warning() {
    msg=$1
    line_number=${BASH_LINENO[0]}
    calling_func=${FUNCNAME[1]}
    echo "$(date +'%d/%m/%Y %H:%M:%S') - [WARNING]  (${calling_func}:${line_number}) ${msg}"
}

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
    echo "### This script allows to handle multiple ACTRIS simulations in the produciton mode. Processing steps are called via Bash"
    echo "### user interface with --flexpart, --softio or --footprint flags. This script can be called via cron tool as well."
    echo "###"
    echo "### Usage : ${bold}${SCRIPT_NAME} [options] arguments${normal}"
    echo "###"
    echo "### Options:"
    echo "###   ${bold}-h|--help${normal}        Show this help message and exit"
    echo "###"
    echo "### Arguments:"
    echo "###   ${bold}-d        list_of_dates.txt${normal}    list of the date/hours to process"
    echo "###   ${bold}-c,--conf configuration.file${normal}  configuration file"
    echo "###"
    echo "### Configuration file is an ASCII file containing paths to source codes and workingd/data directories. The syntaxe is as follows :"
    echo "###    SERVER_USER=\"username\""
    echo "###    LOGS_DIR=\"/path/to/the/directory/where/to/save/log/files\""
    echo "###    PATHS_CONF_FILEPATH=\"/path/to/the/source/configuration.conf\""
    echo "###    LOG_CATALOGUE_FILEPATH=\"/path/to/the/common/log/database.txt\""
    echo "###    FLEXPART_HOUR=\"00\""
    echo "###    DELAY_N_DAYS=5"
    echo "###"
    echo "### --> PATHS_CONF_FILEPATH is the configuration file used by the actris-processing.sh. In this files parameters such as"
    echo "### SRC_DIR, SINGULARITY_FILEPATH and others are set up by the user."
    echo "### --> FLEXPART_HOUR is the start hour of the simulation. For the ACTRIS project it was defined that the simulation will be launched"
    echo "### twice a day, at 00h and 12h."
    echo "### --> DELAY_N_DAYS is the number of days to delay the simulation start from the 'today' date. This can number can be 0,"
    echo "### meaning that the simulation date will be the same as the processing date, but dû to the ECMWF data availability it is not"
    echo "### always possible. Thus this parameter should be adapted based on the delay between 'today' date and the data availability"
    echo "### of the user."
    echo "###"
    echo "### List of the dates is a simple ASCII file where each line is a simulation date/hour to process. Dates should be in the"
    echo "### format YYYYMMDDHH. This list is not mandatory (f.ex. in a case of a cron production this file is not required), but if it"
    echo "### is provided it will overwrite parameters FLEXPART_HOUR and DELAY_N_DAYS set up in the configuration file. This list of dates"
    echo "### can be used to process a particular time period or to re-process particular dates that were not processed or threw an error"
    echo "### during the automatic production."
    echo ""
}

function get_station_ids(){
	exec 2< "${PATHS_CONF_FILEPATH}"
    while read -r line <&2; do
        var_name=$(echo ${line} | cut -d= -f1)
        var_value=$(echo ${line} | cut -d= -f2)
        if [ "${var_name}" == "STATIONS_CONF" ]; then
            var_value=${var_value//\"/""}
            station_ids=($(cat ${var_value} | jq '.[].short_name'))
            break
        fi
    done
    for ii in "${!station_ids[@]}"; do
        station_ids[${ii}]=${station_ids[${ii}]//\"/""}
    done
    exec 2<&-
}

function get_source_dir(){
	exec 2< "${PATHS_CONF_FILEPATH}"
    while read -r line <&2; do
        var_name=$(echo ${line} | cut -d= -f1)
        var_value=$(echo ${line} | cut -d= -f2)
        if [ "${var_name}" == "SRC_DIR" ]; then
            var_value=${var_value//\"/""}
            SRC_DIR=${var_value}
            break
        fi
    done
    exec 2<&-
}

function main(){
    _simu_date=$1
    get_station_ids
    get_source_dir
    jobIDs=""
    # for station in "PDM" "PUY" "RUN" "LTO" "SAC" "OPE"; do
    for station in ${station_ids[@]}; do
        log_filepath="${LOGS_DIR}/${station}/${station}-${_simu_date}.out"
        if [ ! -d "$(dirname ${log_filepath})" ]; then mkdir -p "$(dirname ${log_filepath})"; fi
        info "Submitting job ${station} ${_simu_date}, check log output in the ${log_filepath}"
        id=$(/usr/local/slurm/bin/sbatch \
            --job-name="flexpart-${station}-${_simu_date}" \
            --output="${log_filepath}" \
            --error="${log_filepath}" \
            --wrap="${SRC_DIR}/actris-processing.sh -n ${station} -d ${_simu_date} -c ${PATHS_CONF_FILEPATH} --flexpart")
        id="${id//[!0-9]/}"
        if [ -z ${jobIDs} ]; then
            jobIDs="${id}"
        else
            jobIDs="${jobIDs},${id}"
        fi
    done

    info "Jobs have been sibmitted"

    while true; do
        status=$(/usr/local/slurm/bin/squeue -u ${SERVER_USER} -j ${jobIDs} -h 2>/dev/null)
        if [ ! -z "${status}" ]; then
            # at least one of the jobs is still running
            info "Jobs are still running..."
            sleep 300
        else
            # all of the jobs are done
            break
        fi
    done

    info "FLEXPART is done, proceeding with SOFT-io and footprints"

    IFS=',' read -r -a job_array <<< "${jobIDs}"

    for jobID in ${job_array[@]}; do
        sacct_res=($(/usr/local/slurm/bin/sacct -p -j ${jobID} --noheader -X --format JobName,State))
        job_name=$(echo ${sacct_res} | cut -d'|' -f1)
        job_state=$(echo ${sacct_res} | cut -d'|' -f2)
        station_name=$(echo ${job_name} | cut -d'-' -f2)
        if [[ "${job_state}" == "COMPLETED" ]]; then
            echo "{'processing_date':'$(date +'%d/%m/%Y %H:%M:%S %Z')', 'station_id':'${station_name}', 'simulation_date':'${_simu_date}', 'log_filepath':'${log_filepath}', 'processing_step':'flexpart', 'status':0}" >> ${LOG_CATALOGUE_FILEPATH}
            log_filepath="${LOGS_DIR}/${station_name}/${station_name}-${_simu_date}.out"

            info "SOFT-io processing for ${station_name} ${_simu_date}, log output is in ${log_filepath}"
            /usr/local/slurm/bin/srun \
                --job-name="softio-${station_name}-${_simu_date}" \
                --output="${log_filepath}" \
                --error="${log_filepath}" \
                --open-mode=append \
                ${SRC_DIR}/actris-processing.sh -n ${station_name} -d ${_simu_date} -c ${PATHS_CONF_FILEPATH} --softio
            status=$?
            if [ ${status} == 0 ]; then
                echo "{'processing_date':'$(date +'%d/%m/%Y %H:%M:%S %Z')', 'station_id':'${station_name}', 'simulation_date':'${_simu_date}', 'log_filepath':'${log_filepath}', 'processing_step':'softio', 'status':0}" >> ${LOG_CATALOGUE_FILEPATH}
            else
                echo "{'processing_date':'$(date +'%d/%m/%Y %H:%M:%S %Z')', 'station_id':'${station_name}', 'simulation_date':'${_simu_date}', 'log_filepath':'${log_filepath}', 'processing_step':'softio', 'status':1}" >> ${LOG_CATALOGUE_FILEPATH}
            fi

            info "Footprints image processing for ${station_name} ${_simu_date}, log output is in ${log_filepath}"
            /usr/local/slurm/bin/srun \
                --job-name="footprints-${station_name}-${_simu_date}" \
                --output="${log_filepath}" \
                --error="${log_filepath}" \
                --open-mode=append \
                ${SRC_DIR}/actris-processing.sh -n ${station_name} -d ${_simu_date} -c ${PATHS_CONF_FILEPATH} --footprints
            status=$?
            if [ ${status} == 0 ]; then
                echo "{'processing_date':'$(date +'%d/%m/%Y %H:%M:%S %Z')', 'station_id':'${station_name}', 'simulation_date':'${_simu_date}', 'log_filepath':'${log_filepath}', 'processing_step':'footprints', 'status':0}" >> ${LOG_CATALOGUE_FILEPATH}
            else
                echo "{'processing_date':'$(date +'%d/%m/%Y %H:%M:%S %Z')', 'station_id':'${station_name}', 'simulation_date':'${_simu_date}', 'log_filepath':'${log_filepath}', 'processing_step':'footprints', 'status':1}" >> ${LOG_CATALOGUE_FILEPATH}
            fi
        elif [[ "${job_state}" == "FAILED" ]]; then
            warning "FLEXPART simulation has failed, no SOFT-IO nor footprints processing were launched. Check ${log_filepath} for more information"
            echo "{'processing_date':'$(date +'%d/%m/%Y %H:%M:%S %Z')', 'station_id':'${station_name}', 'simulation_date':'${_simu_date}', 'log_filepath':'${log_filepath}', 'processing_step':'flexpart', 'status':1}" >> ${LOG_CATALOGUE_FILEPATH}
            echo "{'processing_date':'$(date +'%d/%m/%Y %H:%M:%S %Z')', 'station_id':'${station_name}', 'simulation_date':'${_simu_date}', 'log_filepath':'${log_filepath}', 'processing_step':'softio', 'status':1}" >> ${LOG_CATALOGUE_FILEPATH}
            echo "{'processing_date':'$(date +'%d/%m/%Y %H:%M:%S %Z')', 'station_id':'${station_name}', 'simulation_date':'${_simu_date}', 'log_filepath':'${log_filepath}', 'processing_step':'footprints', 'status':1}" >> ${LOG_CATALOGUE_FILEPATH}
        fi
    done
}

function check_args(){
    status=0
    if [ -z ${CONFIG_FILE} ]; then
        error "Configuration file is a mandatory argument. Try again!"
        exit 1
    elif [ ! -f ${CONFIG_FILE} ]; then
        error "Configuration file ${CONFIG_FILE} does not exist. Verify your argument and try again."
        exit 1
    else
        source ${CONFIG_FILE}
    fi
    if [ ! -z ${DATES_FILEPATH} ]; then
        if [ ! -f ${DATES_FILEPATH} ]; then
            error "Provided list of simulation dates/hours ${DATES_FILEPATH} does not exist. Verify your argument and try again."
            exit 1
        fi
    fi
    if [ -z ${SERVER_USER} ]; then error "SERVER_USER argument is mandatory, please verify your configuration file and try again."; status=1; fi
    if [ -z ${LOGS_DIR} ]; then error "LOGS_DIR argument is mandatory, please verify your configuration file and try again."; status=1; fi
    if [ -z ${PATHS_CONF_FILEPATH} ]; then error "PATHS_CONF_FILEPATH argument is mandatory, please verify your configuration file and try again."; status=1; fi
    if [ -z ${LOG_CATALOGUE_FILEPATH} ]; then error "LOG_CATALOGUE_FILEPATH argument is mandatory, please verify your configuration file and try again."; status=1; fi
    if [ -z ${FLEXPART_HOUR} ]; then error "FLEXPART_HOUR argument is mandatory, please verify your configuration file and try again."; status=1; fi
    if [ -z ${DELAY_N_DAYS} ]; then error "DELAY_N_DAYS argument is mandatory, please verify your configuration file and try again."; status=1; fi
    if [ "${status}" == 1 ]; then exit 1; fi
    id -u ${SERVER_USER}
    if [ $? != 0 ]; then
        error "Your username is not valid, please verify your configuration file and try again"
    fi
    if [ ! -d ${LOGS_DIR} ]; then mkdir -p ${LOGS_DIR}; fi
    if [ ! -f ${PATHS_CONF_FILEPATH} ]; then
        error "Paths configuration file ${PATHS_CONF_FILEPATH} does not exist, please verify and try again."
        status=1
    fi
    return ${status}
}

opts=$(getopt --longoptions "help,conf:" --name "$(basename "$0")" --options "h,d:,c:" -- "$@")
eval set -- "$opts"

while [[ $# -gt 0 ]]; do
    case "$1" in
        -c|--conf) shift; CONFIG_FILE=$1; shift;;
        -h|--help) shift; help; exit 0;;
        -d) shift; DATES_FILEPATH=$1; shift;;
        \?) shift; error "Unrecognized options"; exit 1; shift;;
        --) break;;
    esac
done

check_args
if [ "${status}" != 0 ]; then exit ${status}; fi

if [ -z ${DATES_FILEPATH} ]; then
    today=$(date +%s)
    result=$((today - ${DELAY_N_DAYS} * 86400))
    simu_date=$(date -d @$result "+%Y%m%d")${FLEXPART_HOUR}
    info "Launching simulation for ${simu_date}"
    main ${simu_date}
else
    warning "List of simulation dates/hours was provided by the user, FLEXPART_HOUR and DELAY_N_DAYS from the configuration file will not be used."
    info "Provided dates are :"
    #while IFS= read -r simu_date; do
    #    info ${simu_date}
    #done < "${DATES_FILEPATH}"
    info "Going through the list of provided simulation dates..."
    exec 3< "${DATES_FILEPATH}"
    while IFS= read -r simu_date <&3; do
        info "Launching simulation for ${simu_date}"
        main ${simu_date}
    done
    exec 3<&-
fi
