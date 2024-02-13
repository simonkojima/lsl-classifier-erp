# lsl-classifier-erp

# Communication
## Receive
### Train Classifier
type: 'cmd'
cmd: 'train'
After receiving trial, it will be waiting for training data.
See "Receiving Epochs" for the format for sending the Epochs data.

### Start Trial
type: 'cmd'
cmd: 'trial-start'

### Receiving Epochs
epochs: epochs
events: events
use send_sock_split function for sending Epochs data.

### End Trial
type: 'cmd'
cmd: 'trial-end'

## Send

### Training Completed
info: 'training_completed'

### Classification Results
info: 'clasification_result'
output: output
pred: pred

output is containing classifier outputs.
preds is contatining predicted class labels.
