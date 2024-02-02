# Use an official base image with your preferred CUDA version
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV TZ=Europe/London
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get update

RUN apt-get install software-properties-common -y
RUN add-apt-repository ppa:deadsnakes/ppa -y
RUN apt-get install python3.10 -y
RUN apt-get install python3.10-distutils -y
RUN apt-get install python3.10-dev build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev zlib1g-dev -y
RUN apt-get update && apt-get install -y --no-install-recommends gcc
RUN apt-get install curl wget -y
RUN apt-get install linux-libc-dev -y
RUN apt-get install libc6-dev -y
RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python3.10 get-pip.py
RUN apt-get update && apt-get install --no-install-recommends -y build-essential gcc

# Update the package repository and install Git
RUN apt-get update && apt-get install -y git
RUN pip3 install fastapi uvicorn

# Install Python
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
RUN pip install auto-gptq --extra-index-url https://huggingface.github.io/autogptq-index/whl/cu118/
COPY . .
RUN pip3 install -r requirements.txt


# Update the system and install necessary dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libsndfile1 \
    && rm -rf /var/lib/apt/lists/*