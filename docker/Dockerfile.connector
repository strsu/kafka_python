FROM confluentinc/cp-kafka-connect:7.3.0

ENV CONNECT_PLUGIN_PATH='/usr/share/java,/etc/kafka-connect/jars,/usr/share/confluent-hub-components'

RUN confluent-hub install --no-prompt debezium/debezium-connector-mysql:latest \
    && confluent-hub install --no-prompt debezium/debezium-connector-postgresql:2.1.4 \
    && confluent-hub install --no-prompt confluentinc/kafka-connect-datagen:0.4.0 \
    && confluent-hub install --no-prompt confluentinc/kafka-connect-jdbc:10.7.1 \
    && confluent-hub install --no-prompt confluentinc/kafka-connect-s3:10.5.1
