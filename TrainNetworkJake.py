import numpy as np
from keras import models, layers
from matplotlib import pyplot as plt
from keras.datasets import mnist
from keras.utils import to_categorical
from keras.preprocessing.image import ImageDataGenerator
from capsnetKeras.capsulelayers import CapsuleLayer, PrimaryCap, Length, Mask


def main():
    np.set_printoptions(threshold=np.nan)

    number_of_classes = 3
    input_shape = (64, 64, 1)

    x = layers.Input(shape=input_shape)
    '''
    Inputs to the model are MRI images which are down-sampled
    to 64 × 64 from 512 × 512, in order to reduce the number of
    parameters in the model and decrease the training time.
    Second (First?) layer is a convolutional layer with 64 × 9 × 9 filters
    and stride of 1 which leads to 64 feature maps of size 56×56.
    '''
    conv1 = layers.Conv2D(64, (9, 9), activation='relu', name="FirstLayer")(x)
    '''
    The second layer is a Primary Capsule layer resulting from
    256×9×9 convolutions with strides of 2.
    '''
    primaryCaps = PrimaryCap(inputs=conv1, dim_capsule=8,
                             n_channels=32, kernel_size=9, strides=2, padding='valid')
    '''
    Final capsule layer includes 3 capsules, referred to as “Class
    Capsules,’ ’one for each type of candidate brain tumor. The
    dimension of these capsules is 16.
    '''
    capLayer2 = CapsuleLayer(num_capsule=3, dim_capsule=16, routings=2,
                             name="ThirdLayer")(primaryCaps)

    # Layer 4: This is an auxiliary layer to replace each capsule with its
    # length. Just to match the true label's shape.
    # If using tensorflow, this will not be necessary. :)
    out_caps = Length(name='capsnet')(capLayer2)

    # Decoder network.
    y = layers.Input(shape=(number_of_classes,))
    # The true label is used to mask the output of capsule layer. For training
    masked_by_y = Mask()([capLayer2, y])
    # Mask using the capsule with maximal length. For prediction
    masked = Mask()(capLayer2)

    # Shared Decoder model in training and prediction
    decoder = models.Sequential(name='decoder')
    decoder.add(layers.Dense(512, activation='relu',
                             input_dim=16 * number_of_classes))
    decoder.add(layers.Dense(1024, activation='relu'))
    decoder.add(layers.Dense(np.prod(input_shape), activation='sigmoid'))
    decoder.add(layers.Reshape(target_shape=input_shape, name='out_recon'))

    # Models for training and evaluation (prediction)
    train_model = models.Model([x, y], [out_caps, decoder(masked_by_y)])

    train_data_directory = 'train/'
    validation_data_directory = 'test/'
    bsize = 32

    train_generator = create_generator(train_data_directory, batch_size=bsize)

    validation_generator = create_generator(validation_data_directory,
                                            batch_size=bsize)

    print(train_model.summary())

    train_model.compile(
        optimizer="rmsprop",
        loss='mse',
        metrics=['accuracy']
    )

    hst = train_model.fit_generator(
        train_generator,
        steps_per_epoch=72,
        epochs=8,
        validation_data=validation_generator,
        validation_steps=24,
        verbose=1).history

    train_model.save('Test.h5')


def create_generator(data_directory, batch_size=64):
    train_datagen = ImageDataGenerator()
    image_resize_height = 64
    image_resize_width = 64

    generator = train_datagen.flow_from_directory(
        data_directory,
        color_mode='grayscale',
        target_size=(image_resize_height, image_resize_width),
        batch_size=batch_size,
        class_mode='categorical')

    while 1:
        x_batch, y_batch = generator.next()
        yield ([x_batch, y_batch], [y_batch, x_batch])


main()
