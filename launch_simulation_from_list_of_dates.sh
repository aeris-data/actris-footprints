#!/bin/bash

set -e

function info() {
    msg=$1
    line_number=${BASH_LINENO[0]}
    calling_func=${FUNCNAME[1]}
    echo "$(date +'%d/%m/%Y %H:%M:%S') - [INFO]    (${calling_func}:${line_number}) ${msg}"
}

function main(){
    jobIDs=""
    for station in "PDM" "PUY" "RUN" "LTO" "SAC" "OPE"; do
        log_filepath="${logs_dir}/${station}/${station}-${date}.out"
        if [ ! -d "$(dirname ${log_filepath})" ]; then mkdir -p "$(dirname ${log_filepath})"; fi
        info "Submitting job ${station} ${date}, check log output in the ${log_filepath}"
        id=$(/usr/local/slurm/bin/sbatch \
            --job-name="flexpart-${station}-${date}" \
            --output="${log_filepath}" \
            --error="${log_filepath}" \
            --open-mode=append \
            --wrap="/home/resos/git/actris-footprints/launch_simulation_cron.sh -n ${station} -d ${date} -c ${paths_conf_filepath} --flexpart")
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
            sleep 60
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
            # echo "${date};${station_name};flexpart;ok" >> ${catalogue_filepath}
            echo "{'processing_date':'$(date +'%d/%m/%Y %H:%M:%S %Z')', 'station_id':'${station_name}', 'simulation_date':'${date}', 'log_filepath':'${log_filepath}', 'processing_step':'flexpart', 'status':0}" >> ${catalogue_filepath}
            log_filepath="${logs_dir}/${station_name}/${station_name}-${date}.out"

            info "SOFT-io processing for ${station_name} ${date}, log output is in ${log_filepath}"
            /usr/local/slurm/bin/srun \
                --job-name="softio-${station_name}-${date}" \
                --output="${log_filepath}" \
                --error="${log_filepath}" \
                --open-mode=append \
                /home/resos/git/actris-footprints/launch_simulation_cron.sh -n ${station_name} -d ${date} -c ${paths_conf_filepath} --softio
            status=$?
            if [ ${status} == 0 ]; then
                echo "{'processing_date':'$(date +'%d/%m/%Y %H:%M:%S %Z')', 'station_id':'${station_name}', 'simulation_date':'${date}', 'log_filepath':'${log_filepath}', 'processing_step':'softio', 'status':0}" >> ${catalogue_filepath}
            else
                echo "{'processing_date':'$(date +'%d/%m/%Y %H:%M:%S %Z')', 'station_id':'${station_name}', 'simulation_date':'${date}', 'log_filepath':'${log_filepath}', 'processing_step':'softio', 'status':1}" >> ${catalogue_filepath}
            fi

            info "Footprints image processing for ${station_name} ${date}, log output is in ${log_filepath}"
            /usr/local/slurm/bin/srun \
                --job-name="footprints-${station_name}-${date}" \
                --output="${log_filepath}" \
                --error="${log_filepath}" \
                --open-mode=append \
                /home/resos/git/actris-footprints/launch_simulation_cron.sh -n ${station_name} -d ${date} -c ${paths_conf_filepath} --footprint
            status=$?
            if [ ${status} == 0 ]; then
                echo "{'processing_date':'$(date +'%d/%m/%Y %H:%M:%S %Z')', 'station_id':'${station_name}', 'simulation_date':'${date}', 'log_filepath':'${log_filepath}', 'processing_step':'footprints', 'status':0}" >> ${catalogue_filepath}
            else
                echo "{'processing_date':'$(date +'%d/%m/%Y %H:%M:%S %Z')', 'station_id':'${station_name}', 'simulation_date':'${date}', 'log_filepath':'${log_filepath}', 'processing_step':'footprints', 'status':1}" >> ${catalogue_filepath}
            fi
        elif [[ "${job_state}" == "FAILED" ]]; then
            echo "{'processing_date':'$(date +'%d/%m/%Y %H:%M:%S %Z')', 'station_id':'${station_name}', 'simulation_date':'${date}', 'log_filepath':'${log_filepath}', 'processing_step':'flexpart', 'status':1}" >> ${catalogue_filepath}
            echo "{'processing_date':'$(date +'%d/%m/%Y %H:%M:%S %Z')', 'station_id':'${station_name}', 'simulation_date':'${date}', 'log_filepath':'${log_filepath}', 'processing_step':'softio', 'status':1}" >> ${catalogue_filepath}
            echo "{'processing_date':'$(date +'%d/%m/%Y %H:%M:%S %Z')', 'station_id':'${station_name}', 'simulation_date':'${date}', 'log_filepath':'${log_filepath}', 'processing_step':'footprints', 'status':1}" >> ${catalogue_filepath}
        fi
    done
}

SERVER_USER="resos"
logs_dir="/sedoo/resos/actris/LOGS_CRON"
paths_conf_filepath="/home/resos/git/actris-footprints/paths.conf"
catalogue_filepath="/home/resos/git/actris-footprints/SUIVI-PROD-CRON.database"

list_of_dates=$1
# while IFS= read -r date; do
#     info "Date to process : ${date}"
# done < "${list_of_dates}"
while IFS= read -r date; do
    info "Launching simulation for ${date}"
    main
done < "${list_of_dates}"