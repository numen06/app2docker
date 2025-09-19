FROM openjdk:11-jre
    COPY app.jar app.jar
    CMD ["java", "-jar", "app.jar"]
    