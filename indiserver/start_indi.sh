#/bin/bash


args=""

echo "ENVIRONMENT DEFINITION"
echo These environment variables determine the behavior of this container.
echo
echo "INDI_VERBOSE=${INDI_VERBOSE}"
echo
echo "INDI_FIFO_PATH=${INDI_FIFO_PATH}"
echo
echo "INDI_RESTART_COUNT=${INDI_RESTART_COUNT}"
echo
echo "INDI_DRIVERS=${INDI_DRIVERS}"
echo
if [ -z "${INDI_VERBOSE}" ]
then
		INDI_VERBOSE="-v";
fi

if [ -z "${INDI_FIFO_PATH}" ]
then
		echo "Without INDI_FIFO_PATH you can not start/stop drivers at runtime."
		echo
		NO_FIFO=1;
fi

if [ -z "${INDI_RESTART_COUNT}" ]
then
		echo "INDI_RESTART_COUNT set to default (0)."
		echo "indiserver will die after one driver crash."
		echo
		INDI_RESTART_COUNT=0;
fi

if [ -z "${INDI_DRIVERS}" ]
then
		echo "No startup drivers defined with INDI_DRIVERS."
		if [ "${NO_FIFO}" ]
		then
				echo "This Image is useless without at least one of the following defined:";
				echo "Add INDI_FIFO_PATH to dynamically start/stop drivers";
				echo "Add INDI_DRIVERS to start drivers at startup.";
				exit 1;
		fi
fi

if [ "${NO_FIFO}" ]
then
	indiserver -r ${INDI_RESTART_COUNT} ${INDI_VERBOSE} ${INDI_DRIVERS};
else
	indiserver -r ${INDI_RESTART_COUNT} -f ${INDI_FIFO_PATH} ${INDI_VERBOSE} ${INDI_DRIVERS};
fi


