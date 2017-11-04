import h5py
import numpy as np
from keras.layers import Input, Lambda, Activation, AveragePooling2D, UpSampling2D
from keras.models import Model
from keras.layers.merge import multiply
import keras.backend as K

from architectures import build_generator, build_discriminator, sparse_softmax
from ops import scale, inpainting_attention

import sys

if  len(sys.argv)!=3:
    print("This program requires two parameters: inputfile - trained weights, and output file - will contain images generated.")
    sys.exit()

# showers to generate
image_sets = 10 
showers_to_generate = 100000
inputfile = sys.argv[1]
outfile = sys.argv[2]

latent_size = 1024 
# input placeholders
latent = Input(shape=(latent_size, ), name='z') # noise
input_energy = Input(shape=(1, ), dtype='float32') # requested energy of the particle shower
generator_inputs = [latent, input_energy]

# multiply the (scaled) energy into the latent space
h = Lambda(lambda x: x[0] * x[1])([latent, scale(input_energy, 100)])

# build three LAGAN-style generators (checkout out `build_generator` in architectures.py)
img_layer0 = build_generator(h, 3, 96)
img_layer1 = build_generator(h, 12, 12)
img_layer2 = build_generator(h, 12, 6)

# inpainting
# 0 --> 1
zero2one = AveragePooling2D(pool_size=(1, 8))(
    UpSampling2D(size=(4, 1))(
        img_layer0))
img_layer1 = inpainting_attention(img_layer1, zero2one) # this function is in ops.py
# 1 --> 2
one2two = AveragePooling2D(pool_size=(1, 2))(img_layer1)
img_layer2 = inpainting_attention(img_layer2, one2two)
# ^^ pooling and upsampling are needed to reshape images to same dimensions

# outputs
generator_outputs = [
    Activation('relu')(img_layer0),
    Activation('relu')(img_layer1),
    Activation('relu')(img_layer2)
]

# build the actual model
generator = Model(generator_inputs, generator_outputs)

# load trained weights
generator.load_weights(inputfile)

hdf5_file = h5py.File(outfile, mode='w')
hdf5_file.close()

for i in range(image_sets):
    noise = np.random.normal(0, 1, (showers_to_generate, latent_size))
    sampled_energy = np.random.uniform(1, 100, (showers_to_generate, 1))

    images = generator.predict([noise, sampled_energy], verbose=False)
    images = map(lambda x: np.squeeze(x * 1000), images)
    # print(len(images), images[0].shape)
    hdf5_file = h5py.File(outfile, mode='a')
    hdf5_file.create_dataset("images"+str(i), data=images[0])
    hdf5_file.close()

