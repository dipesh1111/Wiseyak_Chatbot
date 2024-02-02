# Use an official base image with your preferred CUDA version
FROM new_chatbot_pytorch

# Copy your models into the Docker image
WORKDIR /usr/src/app
COPY . .

ENV TZ=Europe/London
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Set environment variables if needed
ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES compute,utility
ENV disable_exllama=True

# Expose the necessary port
EXPOSE 80

# Define the command to run your applica
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
