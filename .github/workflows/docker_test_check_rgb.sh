#!/usr/bin/env bash

# Checking the results of running the docker commands

# Define expected results
EXPECTED_FILES=("result.json")
EXPECTED_CANOPYCOVER_VALUES=(99.75714285714285, 20.91874906479126)

# What folder are we looking in for outputs
if [[ ! "${1}" == "" ]]; then
  TARGET_FOLDER="${1}"
else
  TARGET_FOLDER="./outputs"
fi

# What our target file to read is
if [[ ! "${2}" == "" ]]; then
  CHECK_FILE="${2}"
else
  CHECK_FILE="canopycover.csv"
fi
EXPECTED_FILES+=("${CHECK_FILE}")

# Check if expected files are found
for i in $(seq 0 $(( ${#EXPECTED_FILES[@]} - 1 )))
do
  if [[ ! -f "${TARGET_FOLDER}/${EXPECTED_FILES[$i]}" ]]; then
    echo "Expected file ${EXPECTED_FILES[$i]} is missing"
    exit 10
  fi
done

# Check the results of the canopy cover calculation
RESULT_VALUES=(`gawk '
BEGIN {
    FPAT = "([^,]+)|(\"[^\"]+\")"
}
{
  if ($1 != "local_datetime") { # Skipping the header line
    printf("%s\n", $2)
  }
}
END {
}
' "${TARGET_FOLDER}/${CHECK_FILE}"`)

echo "Result counts: ${#EXPECTED_CANOPYCOVER_VALUES[@]} vs ${#RESULT_VALUES[@]}"
if [[ ${#EXPECTED_CANOPYCOVER_VALUES[@]} != ${#RESULT_VALUES[@]} ]]; then
  echo "Number of results found in file (${#RESULT_VALUES[@]}) don't match expected count (${#EXPECTED_CANOPYCOVER_VALUES[@]})"
  if [[ ${#RESULT_VALUES[@]} > 0 ]]; then
    for i in $(seq 0 $(( ${#RESULT_VALUES[@]} - 1 )))
    do
      echo "${i}: ${RESULT_VALUES[$i]}"
    done
  fi
  exit 20
fi

for i in $(seq 0 $(( ${#EXPECTED_CANOPYCOVER_VALUES[@]} - 1 )))
do
  if [[ ${EXPECTED_CANOPYCOVER_VALUES[$i]} != ${RESULT_VALUES[$i]} ]]; then
    echo "Result value for index ${i}: '${RESULT_VALUES[$i]}' doesn't match expected: '${EXPECTED_CANOPYCOVER_VALUES[$i]}'"
    exit 30
  else
    echo "Values for index ${i} match: '${RESULT_VALUES[$i]}' '${EXPECTED_CANOPYCOVER_VALUES[$i]}'"
  fi
done
