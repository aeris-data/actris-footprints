# ACTRIS Footprints

ACTRIS-FR[^1] is the French component of ACTRIS for the observation and exploration of aerosols, clouds and reactive gasses and their interactions. ACTRIS operates central platforms (data and calibration centers) and provides services intended for a large community of users working on chemistry/climate models, on the validation of satellite data or on the analysis of weather forecasting or of air quality.

The objective of this project is to set up a chain of systematic application of FLEXPART and the SOFT-IO tools to the in-situ measurement stations of ACTRIS-France with the development of a subsequent visualization tool. FLEXPART[^2] is a Lagrangian particle dispersion model which makes it possible to estimate the backward trajectories of plumes of aerosol or gas particles. SOFT-IO (“Source attribution using FLEXPART and carbon monoxide emission inventories”)[^3] is a tool developed within SEDOO department of the Observatoire Midi-Pyrénées which allows the estimation of the geographical origin of pollutants and emission sources which are at origin of CO increases in the troposphere and lower stratosphere. Combined with the in-situ measurements of the stations, the products provided by these two tools will serve as a complement for the data analyzes and atmospheric monitoring that SEDOO-AERIS would like to set up and offer to its users.

## Processing chain
Processing chain for this project contains three main steps :
1. FLEXPART backward simulation
2. CO contribution estimation by SOFT-IO
3. creation of the visualization algorithm

The `actris-processing.sh` script allows to manage these three steps (examples below):
```
$ ./actris-processing.sh -n PUY -d 2024050100 --conf ./actris-processing_1.conf --flexpart
$ ./actris-processing.sh -n PUY -d 2024050112 --conf ./actris-processing_1.conf --softio
$ ./actris-processing.sh -n PUY -d 2024050200 --conf ./actris-processing_2.conf --flexpart --footprints
```
The `-n` corresponds to the short ID name of the desired station from the `actris_stations.json` configuration. `-d` is the argument to set up simulation date, the FLEXPART tool will then run in backward mode from this date. `--conf` argument is the configuration file with paths and parameters set up by the user. More information about these parameters can be found in the manual.

## Production chain

The `actris-production.sh` script allows to configure an automatic and regular production of the outputs via cron or slurm tool. This script handles all of the three processing steps for all of the stations defined in the `actris_stations.json` file. This script uses the presented above `actris-processing.sh` script in order to manage different processing steps, but it also serves as an overlay which loops through multiple stations and handles the order of the processing steps. A configuration file `actris-production.conf` is also required by this script. More information can be found in the manual.

Examples of this production script :
```
$ ./actris-production.sh --conf actris-production_1.conf
$ ./actris-production.sh --conf actris-production_2.conf -d dates_to_reprocess.txt
```

[^1]: ACTRIS Climat et qualité de l’air
*https://www.actris.fr/*

[^2]: The Lagrangian particle dispersion model FLEXPART version 10.4
*Pisso, I., Sollum, E., Grythe, H., Kristiansen, N. I., Cassiani, M., Eckhardt, S., Arnold, D., Morton, D., Thompson, R. L., Groot Zwaaftink, C. D., Evangeliou, N., Sodemann, H., Haimberger, L., Henne, S., Brunner, D., Burkhart, J. F., Fouilloux, A., Brioude, J., Philipp, A., Seibert, P., and Stohl, A.: The Lagrangian particle dispersion model FLEXPART version 10.4, Geosci. Model Dev., 12, 4955–4997, https://doi.org/10.5194/gmd-12-4955-2019, 2019*

[^3]: Source attribution using FLEXPART and carbon monoxide emission inventories: SOFT-IO version 1.0
*Sauvage, B., Fontaine, A., Eckhardt, S., Auby, A., Boulanger, D., Petetin, H., Paugam, R., Athier, G., Cousin, J.-M., Darras, S., Nédélec, P., Stohl, A., Turquety, S., Cammas, J.-P., and Thouret, V.: Source attribution using FLEXPART and carbon monoxide emission inventories: SOFT-IO version 1.0, Atmos. Chem. Phys., 17, 15271–15292, https://doi.org/10.5194/acp-17-15271-2017, 2017*
