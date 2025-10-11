# CS329 HW

## Environment Setup (conda + docker)

Download Docker from [here](https://www.docker.com/get-started/). This is necessary to run LLM-generated code, as it isolates the code in a container, making sure potentially harmful code does not directly impact your machine.

We recommend Python 3.11. Create a Conda environment to make package management easier (and download Conda [here](https://www.anaconda.com/download) if you haven't already). 

```bash
# Create & activate environment
conda create -n cs329-hw python=3.11 -y
conda activate cs329-hw

# Run this from the repo root; adjust path if your Dockerfile lives elsewhere
docker build -t humaneval-sandbox -f cs329_hw/run/Dockerfile.sandbox .

# Install Python deps
pip install -r requirements.txt
```
