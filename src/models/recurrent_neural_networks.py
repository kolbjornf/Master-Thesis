# -*- coding: utf-8 -*-
"""SingleModelEvaluation.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/15t0d5lbjgwVoLUU8h9ei0oUIDJEkrLqz
"""

#------- Fix the usage of GPU -----------------------------------------------------

#' ' means CPU whereas '/device:G:0' means GPU
import tensorflow as tf
print(tf.test.gpu_device_name())

# memory footprint support libraries/code
!ln -sf /opt/bin/nvidia-smi /usr/bin/nvidia-smi
!pip install gputil
!pip install psutil
!pip install humanize
import psutil
import humanize
import os
import GPUtil as GPU
GPUs = GPU.getGPUs()
# XXX: only one GPU on Colab and isn’t guaranteed
gpu = GPUs[0]
def printm():
 process = psutil.Process(os.getpid())
 print("Gen RAM Free: " + humanize.naturalsize( psutil.virtual_memory().available ), " | Proc size: " + humanize.naturalsize( process.memory_info().rss))
 print("GPU RAM Free: {0:.0f}MB | Used: {1:.0f}MB | Util {2:3.0f}% | Total {3:.0f}MB".format(gpu.memoryFree, gpu.memoryUsed, gpu.memoryUtil*100, gpu.memoryTotal))
printm()

#!kill -9 -1

from google.colab import drive
drive.mount('/content/drive')

#!google-drive-ocamlfuse -cc

# Code to read csv file into colaboratory:
!pip install -U -q PyDrive
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from google.colab import auth
from oauth2client.client import GoogleCredentials

auth.authenticate_user()
gauth = GoogleAuth()
gauth.credentials = GoogleCredentials.get_application_default()
drive = GoogleDrive(gauth)

downloaded = drive.CreateFile({'id':'1oF7toJFWt-tox50GM8I2AT_fvYITkgzZ'}) # replace the id with id of file you want to access
downloaded.GetContentFile('Data_namechanged.pkl')

# Commented out IPython magic to ensure Python compatibility.
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
# %matplotlib inline
import math
import time
import scipy
from sklearn.decomposition import PCA
from sklearn.metrics import mean_squared_error
from sklearn.metrics import mean_absolute_error

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers


from sklearn.preprocessing import MinMaxScaler, StandardScaler

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Input, Dense, GRU, Dropout, LSTM, SimpleRNN, LeakyReLU, ReLU
from tensorflow.keras.optimizers import RMSprop, Adagrad, Adam
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, TensorBoard, ReduceLROnPlateau
from tensorflow.keras.backend import square, mean, sqrt, sum, epsilon, abs
from tensorflow.keras.losses import MeanSquaredError

from tensorflow.keras.preprocessing.sequence import TimeseriesGenerator
from statsmodels.tsa.arima_model import ARIMA

def batch_generator_chron(batch_size, sequence_length, num_x_signals, num_y_signals, num_train, x_train_scaled, y_train_scaled):
   
    while True:
        x_shape = (batch_size, sequence_length, num_x_signals)
        x_batch = np.zeros(shape=x_shape, dtype=np.float16)

        y_shape = (batch_size, sequence_length, num_y_signals)
        y_batch = np.zeros(shape=y_shape, dtype=np.float16)
        idx = 0
        step_size = int(sequence_length/2)
        for i in range(batch_size-1):
            x_batch[i] = x_train_scaled[idx:idx+sequence_length]
            y_batch[i] = y_train_scaled[idx:idx+sequence_length]
            idx = idx + step_size
        
        yield (x_batch, y_batch)

warmup_steps = 50
def rmse_warmup(y_true, y_pred, warmup = True):
    if warmup:
      y_true_slice = y_true[:, warmup_steps:, :]
      y_pred_slice = y_pred[:, warmup_steps:, :]
      rmse = sqrt(mean(square(y_pred_slice - y_true_slice), axis=-1)) 
    else:
      rmse = sqrt(mean(square(y_pred - y_true))) 
    return rmse

warmup_steps = 50
def mse_warmup(y_true, y_pred, warmup = True):
    if warmup:
      y_true_slice = y_true[:, warmup_steps:, :]
      y_pred_slice = y_pred[:, warmup_steps:, :]
      mse = mean(square(y_true_slice - y_pred_slice))
    else:
      mse = mean(square(y_true - y_pred))
    return mse

warmup_steps = 50
def mae_warmup(y_true, y_pred, warmup = True):
    if warmup:
      y_true_slice = y_true[:, warmup_steps:, :]
      y_pred_slice = y_pred[:, warmup_steps:, :]
      mae = mean(abs(y_true_slice - y_pred_slice))
    else:
      mae = mean(abs(y_true - y_pred))
    return mae

def r_square_warmup(y_true, y_pred, warmup = True):
    if warmup:
      y_true_slice = y_true[:, warmup_steps:, :]
      y_pred_slice = y_pred[:, warmup_steps:, :]
      SS_res =  sum(square(y_true_slice - y_pred_slice)) 
      SS_tot = sum(square(y_true_slice - mean(y_true_slice))) 
      r_square = ( 1 - SS_res/(SS_tot + epsilon()) )
    else:
      SS_res =  sum(square(y_true - y_pred)) 
      SS_tot = sum(square(y_true - mean(y_true))) 
      r_square = ( 1 - SS_res/(SS_tot + epsilon()) )
    return r_square

data = pd.read_pickle('Data_namechanged.pkl')
arima = pd.read_csv('predictions_arima.csv')
data = data.reset_index()
data = data.drop(['DateTime'], axis = 1)
data = data[['Control Flow Indicator CC1', 'Suction Gas Pressure CB2',
       'Suction Gas Temperature CC2', 'Discharge Pressure GTC',
       'Speed Set Point GTC', 'Producer Speed GTC', 'RPM Turbine C',
       'Control Flow Indicator CB3.1', ' T5 GTC',
       'Discharge Gas Temperature CB2', 'OPRA3 Gas Temperature',
       ' Discharge Gas Temperature CC1', 'Suction Gas Pressure CC2',
       'Discharge Gas Temprature CC3', 'Discharge Gas Temprature CB3',
       'Suction Gas Temperature CC1', ' Discharge Gas Temperature CC2',
       'Discharge Gas Pressure CC2', 'Suction Gas Pressure CC1',
       'RPM Turbine B', 'Suction Gas Pressure CB3', 'Wind Direction 2 ',
       'OPRA1 Gas Temperature', 'Suction Gas Pressure CC3',
       'Control Flow Indicator CC2', 'Suction Gas Pressure CA2',
       'Discharge Gas Pressure CA3', 'Discharge Gas Pressure CB2', ' T5 GTB',
       'RPM Turbine A', 'Speed Set Point GTA', 'Discharge Gas Pressure CA1',
       'Discharge Gas Pressure CC3', 'T5 GTA', 'Discharge Gas Temperature CB1',
       'Discharge Gas Temperature CA1', 'Air Inlet Temperature - GTA',
       'Suction Gas Temperature CA1', ' Control Flow Indicator CA3',
       'OPRA2 Gas Temperature', 'Suction Gas Pressure CA1',
       'Suction Gas Temperature CB2', 'Discharge Gas Pressure CB3',
       'Suction Gas Temprature CA3', 'Deg Heading',
       'Control Flow Indicator CB3', 'Suction Gas Temprature CB3',
       'Control Flow Indicator CB2', 'Discharge Pressure GTA', 'HP Flare']]
data = data.interpolate(method='linear') 
df_targets = data.pop('HP Flare')

if False:
  pca = PCA(n_components = 0.999)
  projected = pca.fit_transform(data)
  data = pd.DataFrame(projected)

def run_model(data):
  time_start = time.clock()
  x_data = data.values
  y_data = df_targets.values.reshape(-1,1)

  num_data = len(x_data)
  train_split = 0.8
  validation_split = 0.2
  num_train = int(train_split * num_data)
  num_test = num_data - num_train

  x_train = x_data[0:num_train]
  x_test = x_data[num_train:]
  y_train = y_data[0:num_train]
  y_test = y_data[num_train:]


  num_x_signals = x_data.shape[1]
  num_y_signals = y_data.shape[1]

  x_scaler = MinMaxScaler()
  x_train_scaled_t = x_scaler.fit_transform(x_train)
  x_test_scaled = x_scaler.transform(x_test)

  y_scaler = MinMaxScaler()
  y_train_scaled_t = y_scaler.fit_transform(y_train)
  y_test_scaled = y_scaler.transform(y_test)

  num_train = int((1-validation_split) * num_train)
  num_val = num_train * validation_split

  x_train_scaled = x_train_scaled_t[0:num_train]
  x_val_scaled = x_train_scaled_t[num_train:]
  y_train_scaled = y_train_scaled_t[0:num_train]
  y_val_scaled = y_train_scaled_t[num_train:]

  validation_data = (np.expand_dims(x_val_scaled, axis=0), np.expand_dims(y_val_scaled, axis=0))

  print(x_data.shape, y_data.shape, x_train_scaled.shape, y_train_scaled.shape, x_val_scaled.shape, y_val_scaled.shape, x_test_scaled.shape, y_test_scaled.shape)

  
  model = Sequential()
  model.add(LSTM(units=50, return_sequences=True, input_shape = (None, num_x_signals,), activation = 'tanh'))
  model.add(Dropout(0.3))
  model.add(LSTM(units=50, return_sequences=True, activation = 'tanh'))
  model.add(Dropout(0.3))
  model.add(Dense(1, activation= 'linear'))
  model.add(LeakyReLU(alpha=0.05))

  #optimizer = RMSprop(lr=1e-3) #1e-3
  optimizer = Adam(lr=1e-3) #1e-3
  model.compile(loss= 'mse', optimizer=optimizer, metrics = [rmse_warmup, mse_warmup, mae_warmup, r_square_warmup])

  path_checkpoint = 'best_model'
  callback_checkpoint = ModelCheckpoint(filepath=path_checkpoint, monitor='val_loss', verbose=1, save_weights_only=True, save_best_only=True)
  callback_early_stopping = EarlyStopping(monitor='val_loss', patience=3, verbose=1)
  callbacks = [callback_checkpoint, callback_early_stopping]

  sequence_length = 200
  batch_size = int(math.ceil(len(x_train_scaled)/sequence_length)*1.5)
  steps_per_epoch = int(math.ceil(len(x_train_scaled)/batch_size))
  print('Batch size: {}'.format(batch_size))
  print('Steps per epoch: {}'.format(steps_per_epoch))

  generator_v3 = batch_generator_chron(batch_size, sequence_length, num_x_signals, num_y_signals, num_train, x_train_scaled, y_train_scaled)

  hist = model.fit(x=generator_v3, epochs = 15, steps_per_epoch = steps_per_epoch, validation_data = validation_data, callbacks = callbacks)

  print('Time elapsed: {}'.format(time.clock() - time_start))

  try:
    model.load_weights(path_checkpoint)
    print('Success')
  except Exception as error:
    print("Error trying to load checkpoint.")
    print(error)

  x_t = np.expand_dims(x_train_scaled_t, axis=0)
  y_pred_t = model.predict(x_t)
  y_pred_rescaled_t = y_scaler.inverse_transform(y_pred_t[0])
  
  # Use the model to predict the output-signals.
  x = np.expand_dims(x_test_scaled, axis=0)
  y_pred = model.predict(x)
  y_pred_rescaled = y_scaler.inverse_transform(y_pred[0])

  x_v = np.expand_dims(x_val_scaled, axis=0)
  y_pred_v = model.predict(x_v)
  y_pred_rescaled_v = y_scaler.inverse_transform(y_pred_v[0])

  final_rmse = rmse_warmup(y_test, y_pred_rescaled, warmup=False)
  final_mse = mean_squared_error(y_test, y_pred_rescaled)
  final_mae = mean_absolute_error(y_test, y_pred_rescaled)

  #final_mse = mse_warmup(y_test, y_pred_rescaled, warmup=False)
  #final_mae = mae_warmup(y_test, y_pred_rescaled, warmup=False)
  #final_rsquare = r_square_warmup(y_test, y_pred_rescaled, warmup=False)

  final_rmse_t = rmse_warmup(y_train, y_pred_rescaled_t, warmup=False)
  final_mse_t = mean_squared_error(y_train, y_pred_rescaled_t)
  final_mae_t = mean_absolute_error(y_train, y_pred_rescaled_t)
  
  #final_mse_t = mse_warmup(y_train, y_pred_rescaled_t, warmup=False)
  #final_mae_t = mae_warmup(y_train, y_pred_rescaled_t, warmup=False)
  #final_rsquare_t = r_square_warmup(y_train, y_pred_rescaled_t, warmup=False)

  cor_y_val = y_scaler.inverse_transform(y_val_scaled)
  final_rmse_v = rmse_warmup(cor_y_val, y_pred_rescaled_v, warmup=False)
  final_mse_v = mean_squared_error(cor_y_val, y_pred_rescaled_v)
  final_mae_v = mean_absolute_error(cor_y_val, y_pred_rescaled_v)

  #final_mse_v = mse_warmup(cor_y_val, y_pred_rescaled_v, warmup=False)
  #final_mae_v = mae_warmup(cor_y_val, y_pred_rescaled_v, warmup=False)
  #final_rsquare_t = r_square_warmup(y_train, y_pred_rescaled_t, warmup=False)
 

  return  y_pred_rescaled, y_test, y_pred_rescaled_t, y_train, y_pred_rescaled_v, cor_y_val, final_rmse, final_rmse_t, final_rmse_v , final_mse, final_mse_t, final_mse_v, final_mae, final_mae_t , final_mae_v , hist# final_rsquare

output = run_model(data)

plt.figure(figsize=(15,5))
plt.plot(output[15].history['loss'], label = 'Training Loss')
plt.plot(output[15].history['val_loss'], label = 'Validation Loss')
plt.ylabel('MSE')
plt.xlabel('Epoch')
plt.legend()
plt.show

def plot_comparison(y_pred, y_true):
    
    #y_pred_rescaled = y_scaler.inverse_transform(y_pred)
    #y_true_rescaled = y_scaler.inverse_transform(y_true)
    y_pred_rescaled = y_pred
    y_true_rescaled = y_true
    

    # Make the plotting-canvas bigger.
    plt.figure(figsize=(15,5))
    
    # Plot and compare the two signals.
    if False:
      plt.plot(y_true_rescaled[:], label='Correct Target Value')
      plt.plot(y_pred_rescaled[:], label='Predicted Target Value')

    if True:
      plt.plot(y_true_rescaled[6425:6500], label='Correct Target Value')
      plt.plot(y_pred_rescaled[6425:6500], label='Predicted Target Value')
      plt.title('LSTM')
    
    # Plot grey box for warmup-period.
    #p = plt.axvspan(0, warmup_steps, facecolor='black', alpha=0.15)
    
    # Plot labels etc.
    plt.ylabel('HP Flare kg/h')
    plt.xlabel('Hours')
    plt.legend()
    plt.show()

plot_comparison(output[0], output[1])
np.sum(output[0] < 0, axis=0)

plot_comparison(output[2], output[3])

plot_comparison(output[4], output[5])

print('Test Scores: \n')
print('Average RMSE: {}'.format(output[6]))
print('Average MSE: {}'.format(output[9]))
print('Average MAE: {}'.format(output[12]))
#print('Average R_square: {}'.format(output[15]))

print('Train Scores: \n')
print('Average RMSE: {}'.format(output[7]))
print('Average MSE: {}'.format(output[10]))
print('Average MAE: {}'.format(output[13]))
#print('Average R_square: {}'.format(output[16]))

print('Validation Scores: \n')
print('Average RMSE: {}'.format(output[8]))
print('Average MSE: {}'.format(output[11]))
print('Average MAE: {}'.format(output[14]))
#print('Average R_square: {}'.format(output[17]))

