import pandas as pd
import numpy as np
from tqdm import tqdm
import cv2
from sklearn.model_selection import train_test_split
import keras
from keras.applications.vgg19 import VGG19
from keras.models import Model
from keras.layers import Dense, Flatten

df_train = pd.read_csv('./labels.csv')
df_test = pd.read_csv('./sample_submission.csv')

targets_series = pd.Series(df_train['breed'])

# One hot encoding for the targets
# breed0 -> [1,0,0,0,...,0]
one_hot = pd.get_dummies(targets_series, sparse=True)
one_hot_labels = np.asarray(one_hot)

# Image size to resize dataset
im_size = 120

i = 0
x_train = []
y_train = []
x_test = []

# We use tqdm to generate nice progress bars
# Then we load the image, resize and append to the train dataset
for f, breed in tqdm(df_train.values):
    img = cv2.imread('./train/{}.jpg'.format(f))
    label = one_hot_labels[i]
    x_train.append(cv2.resize(img, (im_size, im_size)))
    y_train.append(label)
    i += 1

# Convert values to correct type for optimizations
y_train_raw = np.array(y_train, np.uint8)
x_train_raw = np.array(x_train, np.float32)

# Data normalization
mean = x_train_raw.mean()
std = x_train_raw.std()
x_train_raw = (x_train_raw - mean) / std

# Printing the shape of the datasets
print(x_train_raw.shape)
print(y_train_raw.shape)

num_class = y_train_raw.shape[1]

# Dataset split into train and validation datasets
X_train, X_valid, Y_train, Y_valid = train_test_split(x_train_raw, y_train_raw, test_size=0.3, random_state=1)

# Create the base pre-trained model
base_model = VGG19(weights='imagenet', include_top=False, input_shape=(im_size, im_size, 3))

# Add a new top layers
x = base_model.output
x = Flatten()(x)
x = Dense(1024, activation='sigmoid')(x)
x = Dense(512, activation='sigmoid')(x)
x = Dense(256, activation='sigmoid')(x)
prediction_layer = Dense(num_class, activation='softmax')(x)

# This is the model we will train
model = Model(inputs=base_model.input, outputs=prediction_layer)

# First: train only the top layers (which were randomly initialized)
for layer in base_model.layers:
    layer.trainable = False

model.compile(loss='categorical_crossentropy',
              optimizer='adam',
              metrics=['accuracy'])

# Callback to stop if val_acc stop improving
callbacks_list = [keras.callbacks.EarlyStopping(monitor='val_acc', patience=3, verbose=1)]
model.summary()

# Fitting the model
model.fit(X_train, Y_train, epochs=10, validation_data=(X_valid, Y_valid), verbose=1, callbacks=callbacks_list)

# Load the data for the test dataset
for f in tqdm(df_test['id'].values):
    img = cv2.imread('./test/{}.jpg'.format(f))
    x_test.append(cv2.resize(img, (im_size, im_size)))

x_test = np.array(x_test, np.float32)
x_test = (x_test - mean) / std

# Making predictions about the test data
predictions = model.predict(x_test, verbose=1)


sub = pd.DataFrame(predictions)
# Set column names to those generated by the one-hot encoding earlier
col_names = one_hot.columns.values
sub.columns = col_names
# Insert the column id from the sample_submission at the start of the data frame
sub.insert(0, 'id', df_test['id'])

# Save the data to make a submission to the kaggle
sub.to_csv('submission.csv', index=False)

# Save model file
model.save('model.h5')
