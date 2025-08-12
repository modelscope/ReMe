## BFCL installation
git clone https://github.com/ShishirPatil/gorilla.git

#### Change directory to the `berkeley-function-call-leaderboard`
cd gorilla/berkeley-function-call-leaderboard

### Install the package in editable mode
pip install -e .

#### Move the dataset to the data folder under bfcl
cp -r gorilla/berkeley-function-call-leaderboard/bfcl_eval/data {/path/to/bfcl/data}