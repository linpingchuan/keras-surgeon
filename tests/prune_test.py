import pytest
import numpy as np

from kerasprune.prune import delete_channels
from kerasprune.prune import rebuild_sequential
from kerasprune.prune import rebuild
from kerasprune import prune


@pytest.fixture
def model_1():
    """Basic Lenet-style model test fixture with minimal channels"""
    from keras.models import Sequential
    from keras.layers import Dense, Conv2D, Flatten
    model = Sequential()
    model.add(Conv2D(2, [3, 3], input_shape=[28, 28, 1], data_format='channels_last', activation='relu'))
    model.add(Conv2D(2, [3, 3], activation='relu'))
    model.add(Flatten())
    model.add(Dense(2, activation='relu'))
    model.add(Dense(10, activation='relu'))
    return model


@pytest.fixture
def model_2():
    """Basic Lenet-style model test fixture with minimal channels"""
    from keras.models import Model
    from keras.layers import Dense, Conv2D, Flatten
    model = model_1()
    return Model(model.inputs, model.outputs)


def test_delete_channel_conv2d_conv2d(model_1):
    layer_index = 0
    channels_index = [0]
    new_model = delete_channels(model_1, layer_index, channels_index)
    weights = model_1.layers[layer_index].get_weights()
    new_weights = new_model.layers[layer_index].get_weights()
    assert np.array_equal(weights[0][:, :, :, 1:], new_weights[0])
    assert np.array_equal(weights[1][1:], new_weights[1])
    weights = model_1.layers[layer_index+1].get_weights()
    new_weights = new_model.layers[layer_index+1].get_weights()
    assert np.array_equal(weights[0][:, :, 1:, :], new_weights[0])
    assert np.array_equal(weights[1], new_weights[1])


def test_delete_channel_dense_dense(model_1):
    layer_index = 3
    channels_index = [0]
    new_model = delete_channels(model_1, layer_index, channels_index)
    weights = model_1.layers[layer_index].get_weights()
    new_weights = new_model.layers[layer_index].get_weights()
    assert np.array_equal(weights[0][:, 1:], new_weights[0])
    assert np.array_equal(weights[1][1:], new_weights[1])
    weights = model_1.layers[layer_index+1].get_weights()
    new_weights = new_model.layers[layer_index + 1].get_weights()
    assert np.array_equal(weights[0][1:, :], new_weights[0])
    assert np.array_equal(weights[1], new_weights[1])


def test_delete_channel_conv2d_dense(model_1):
    layer_index = 1
    channels_index = [0]
    new_model = delete_channels(model_1, layer_index, channels_index)
    weights = model_1.layers[layer_index].get_weights()
    new_weights = new_model.layers[layer_index].get_weights()
    assert np.array_equal(weights[0][:, :, :, 1:], new_weights[0])
    assert np.array_equal(weights[1][1:], new_weights[1])
    weights = model_1.layers[layer_index+2].get_weights()
    new_weights = new_model.layers[layer_index + 2].get_weights()
    assert np.array_equal(np.delete(weights[0], slice(0, None, 2), axis=0), new_weights[0])
    assert np.array_equal(weights[1], new_weights[1])


def test_rebuild_sequential(model_1):
    new_model = rebuild_sequential(model_1)


def test_rebuild(model_2):
    from tensorflow.examples.tutorials.mnist import input_data
    model_2.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    mnist = input_data.read_data_sets('tempData', one_hot=True, reshape=False)
    new_model = rebuild(model_2)
    new_model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    loss = model_2.evaluate(mnist.validation.images, mnist.validation.labels, 128)
    loss2 = model_2.evaluate(mnist.validation.images, mnist.validation.labels, 128)
    assert np.allclose(loss, loss2, atol=1e-6)


def test_delete_channels_rec_1():
    from keras.layers import Input, Dense
    from keras.models import Model
    from kerasprune.prune import delete_channels_rec
    inputs = Input(shape=(784,))
    x = Dense(64, activation='relu')(inputs)
    x = Dense(64, activation='relu')(x)
    predictions = Dense(10, activation='softmax')(x)

    model = Model(inputs=inputs, outputs=predictions)
    model.compile(optimizer='rmsprop',
                  loss='categorical_crossentropy',
                  metrics=['accuracy'])
    new_model = delete_channels_rec(model, model.layers[2], [0])


@pytest.fixture
def model_3():
    from keras.layers import Input, Dense, Conv2D, MaxPool2D, Flatten
    from keras.models import Model
    main_input = Input(shape=[7, 7, 1])
    x = Conv2D(3, [3, 3], data_format='channels_last')(main_input)
    x = Conv2D(3, [3, 3], data_format='channels_last')(x)
    x = Flatten()(x)
    x = Dense(3)(x)
    main_output = Dense(1)(x)

    model = Model(inputs=main_input, outputs=main_output)

    # Set all of the weights
    w1 = [np.asarray([[[[1, 2, 3]], [[4, 5, 6]], [[7, 8, 9]]],
                      [[[10, 11, 12]], [[13, 14, 15]], [[16, 17, 18]]],
                      [[[19, 20, 21]], [[22, 23, 24]], [[25, 26, 27]]]],
                     dtype='float32'),
          np.asarray([100, 200, 300], dtype='float32')]
    model.layers[1].set_weights(w1)
    w2 = [
        np.reshape(np.arange(0, 3 * 3 * 3 * 3, dtype='float32'), [3, 3, 3, 3]),
        np.asarray([100, 200, 300], dtype='float32')]
    model.layers[2].set_weights(w2)

    w4 = [np.reshape(np.arange(0, 3 * 3 * 3 * 3, dtype='float32'),
                     [3 * 3 * 3, 3]),
          np.asarray([100, 200, 300], dtype='float32')]
    model.layers[4].set_weights(w4)
    model.compile(optimizer='rmsprop',
                  loss='categorical_crossentropy',
                  metrics=['accuracy'])
    return model


@pytest.mark.parametrize("channel_index", [
    [0],
    [1],
    [2],
    [0, 1]
    # pytest.param("6*9", 42, marks=pytest.mark.xfail),
])
def test_delete_channels_rec_conv2d_conv2d(model_3, channel_index):
    from kerasprune.prune import delete_channels_rec
    layer_index = 1
    # next_layer_index = 2
    new_model = delete_channels_rec(model_3,
                                    model_3.layers[layer_index],
                                    channel_index,
                                    copy=True)
    w = model_3.layers[layer_index].get_weights()
    correct_w = [np.delete(w[0], channel_index, axis=-1),
                 np.delete(w[1], channel_index, axis=0)]
    new_w = new_model.layers[layer_index].get_weights()
    assert weights_equal(correct_w, new_w)


@pytest.mark.parametrize("channel_index", [
    [0],
    [1],
    [2],
    [0, 1]
])
def test_delete_channels_rec_conv2d_conv2d_next_layer(model_3, channel_index):
    from kerasprune.prune import delete_channels_rec
    layer_index = 1
    next_layer_index = 2
    new_model = delete_channels_rec(model_3,
                                    model_3.layers[layer_index],
                                    channel_index)
    w = model_3.layers[next_layer_index].get_weights()
    correct_w = [np.delete(w[0], channel_index, axis=-2),
                 w[1]]
    new_w = new_model.layers[next_layer_index].get_weights()
    assert weights_equal(correct_w, new_w)


def weights_equal(w1, w2):
    if len(w1) != len(w2):
        return False
    else:
        return all([np.array_equal(w1[i], w2[i]) for i in range(len(w1))])


def test_delete_layer():
    from keras.layers import Input, Dense, Conv2D, MaxPool2D, Flatten
    from keras.models import Model
    # Create all model layers
    input_1 = Input(shape=[7, 7, 1])
    conv2d_1 = Conv2D(3, [3, 3], data_format='channels_last')
    conv2d_2 = Conv2D(3, [3, 3], data_format='channels_last')
    flatten_1 = Flatten()
    dense_1 = Dense(3)
    dense_2 = Dense(3)
    dense_3 = Dense(3)
    dense_4 = Dense(1)
    # Create the model and expected modified model
    output_1 = dense_4(dense_3(dense_2(dense_1(flatten_1(conv2d_2(conv2d_1(input_1)))))))
    output_2 = dense_4(dense_3(dense_1(flatten_1(conv2d_2(conv2d_1(input_1))))))
    model_1 = prune.clean_copy(Model(inputs=input_1, outputs=output_1))
    model_2_exp = prune.clean_copy(Model(inputs=input_1, outputs=output_2))
    # Delete the layer
    delete_layer_index = 5
    model_2 = prune.delete_layer(model_1, model_1.layers[delete_layer_index])
    # Compare the modified model with the expected modified model
    config = model_2.get_config()
    config_exp = model_2_exp.get_config()
    config_exp['name'] = config['name']
    assert(config == config_exp)
    assert(all([np.array_equal(weight, weight_exp) for (weight, weight_exp) in
                zip(model_2.get_weights(), model_2_exp.get_weights())]))


def test_delete_layer_reuse():
    from keras.layers import Input, Dense, Conv2D, MaxPool2D, Flatten
    from keras.models import Model
    # Create all model layers
    input_1 = Input(shape=[3])
    dense_1 = Dense(3)
    dense_2 = Dense(3)
    dense_3 = Dense(3)
    dense_4 = Dense(3)
    # Create the model and expected modified model
    x = dense_1(input_1)
    x = dense_2(x)
    x = dense_3(x)
    x = dense_2(x)
    output_1 = dense_4(x)
    # model_1 = prune.clean_copy(Model(inputs=input_1, outputs=output_1))
    model_1 = Model(inputs=input_1, outputs=output_1)

    x = dense_1(input_1)
    x = dense_3(x)
    output_2 = dense_4(x)
    # model_2_exp = prune.clean_copy(Model(inputs=input_1, outputs=output_2))
    model_2_exp = Model(inputs=input_1, outputs=output_2)
    # Delete the layer
    delete_layer_index = 2
    model_2 = prune.delete_layer(model_1, model_1.layers[delete_layer_index],
                                 copy=False)
    # Compare the modified model with the expected modified model
    config = model_2.get_config()
    config_exp = model_2_exp.get_config()
    config_exp['name'] = config['name']
    assert (config == config_exp)
    assert (all([np.array_equal(weight, weight_exp) for (weight, weight_exp) in
                 zip(model_2.get_weights(), model_2_exp.get_weights())]))


def test_replace_layer():
    from keras.layers import Input, Dense, Conv2D, MaxPool2D, Flatten
    from keras.models import Model
    # Create all model layers
    input_1 = Input(shape=[7, 7, 1])
    dense_1 = Dense(3)
    dense_2 = Dense(3)
    dense_3 = Dense(3)
    dense_4 = Dense(1)
    # Create the model and expected modified model
    x = dense_1(input_1)
    x = dense_2(x)
    output_1 = dense_4(x)
    model_1 = prune.clean_copy(Model(inputs=input_1, outputs=output_1))

    x = dense_1(input_1)
    x = dense_3(x)
    output_2 = dense_4(x)
    model_2_exp = prune.clean_copy(Model(inputs=input_1, outputs=output_2))

    # Delete the layer
    layer_index = 2
    model_2 = prune.replace_layer(model_1, model_1.layers[layer_index], dense_3)
    # Compare the modified model with the expected modified model
    config = model_2.get_config()
    config_exp = model_2_exp.get_config()
    config_exp['name'] = config['name'] # make the config names identical
    assert(config == config_exp)
    assert(all([np.array_equal(weight, weight_exp) for (weight, weight_exp) in
                zip(model_2.get_weights(), model_2_exp.get_weights())]))
# def delete_conv2d_filters(model, layer):
#     return model
#
#
# # content of test_expectation.py
# @pytest.mark.parametrize("test_input,expected", [
#     ("3+5", 8),
#     ("2+4", 6),
#     pytest.param("6*9", 42,
#                  marks=pytest.mark.xfail),
# ])
# def test_eval(test_input, expected):
#     assert eval(test_input) == expected

if __name__ == '__main__':
    pytest.main([__file__])
