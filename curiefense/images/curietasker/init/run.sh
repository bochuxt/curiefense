#!/bin/bash
set -o pipefail

# initialize db if needed.
URL="${CURIECONF_BASE_URL:-http://confserver/api/v1/}"
DBNAME="${CURIETASKER_DB_NAME:-tasks}"

CURL="curl --silent --show-error --fail"

echo "Determining whether the $DBNAME DB should be created..."
RETRIES=0
STATUS=1
until [ "$RETRIES" -ge 10 ]
do
	if DBLIST=$($CURL -X GET "${URL}db/" -H  'accept: application/json'); then
		STATUS=0
		break
	fi
	sleep 5
	RETRIES=$((RETRIES+1))
done

if [ "$STATUS" -eq 1 ]; then
	echo "Could not determine whether the $DBNAME DB should be created, exiting." > /dev/stderr
	exit 1
fi

if echo "$DBLIST" | grep -q "$DBNAME"; then
	echo "The $DBNAME database already exists."
else
	echo "Initializing the $DBNAME database..."
	RETRIES=0
	STATUS=1
	until [ "$RETRIES" -ge 10 ]
	do
		if $CURL -X POST "${URL}db/$DBNAME/" -H 'accept: application/json' -H 'Content-Type: application/json' -d '{"tasklist":[]}'; then
			STATUS=0
			break
		fi
		sleep 5
		RETRIES=$((RETRIES+1))
	done
	if [ "$STATUS" -eq 1 ]; then
		echo "Error while creating the $DBNAME DB, exiting." > /dev/stderr
		exit 1
	fi
	echo "The $DBNAME database has been created."
fi

# run curietasker
/usr/bin/python3 /usr/local/bin/curietasker start
