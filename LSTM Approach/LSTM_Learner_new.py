from __future__ import print_function

import numpy as np
import tensorflow as tf
from tensorflow.contrib import rnn
import random
import time
import LSTM_preprocess2
import LSTM_8to1Preprocessing
import xml_to_midi_for_testing
from music21 import converter
import os

start_time = time.time()
def elapsed(sec):
    if sec<60:
        return str(sec) + " sec"
    elif sec<(60*60):
        return str(sec/60) + " min"
    else:
        return str(sec/(60*60)) + " hr"


# Target log path
logs_path = './'
writer = tf.summary.FileWriter(logs_path)

# Text file containing words for training
training_file = './belling_the_cat.txt'

# def read_data(fname):
#     with open(fname) as f:
#         content = f.readlines()
#     content = [x.strip() for x in content]
#     content = [content[i].split() for i in range(len(content))]
#     content = np.array(content)
#     content = np.reshape(content, [-1, ])
#     return content

training_path = '../599'
book_interval, book_finger = LSTM_preprocess2.main(training_path)
input_list, label_list = LSTM_8to1Preprocessing.main(book_interval, book_finger)
os.chdir("..")
# training_data = read_data(training_file)
print("Loaded training data...")

def getTestData():

    piece = converter.parse('LSTM_test.xml')
    testing_midi = xml_to_midi_for_testing.main(piece)
    testing_midi_array = np.array(testing_midi)
    testing_interval_array = np.diff(testing_midi_array)

    first_two_fingers = [1, 2, 3]

    a = first_two_fingers[0]
    b = testing_interval_array[0]
    c = first_two_fingers[1]
    d = testing_interval_array[1]
    e = first_two_fingers[2]
    f = testing_interval_array[2]

    first_testing_input = [a,b,c,d,e,f]
    # a = (first_two_fingers[0] - 1) * 25 + (testing_interval_array[0] + 13) 
    # b = (first_two_fingers[1] - 1) * 25 + (testing_interval_array[1] + 13) 
    # first_testing_input = [a,b]
    return testing_interval_array, first_testing_input


# def fingerToNum(fingering):
#     return fingering[0] * 10 + fingering[1]

# def build_dataset(fingering_list):
#     # print(count)
#     dictionary = dict()
#     idx = 0
#     for fingering in fingering_list:
#         for each_fingering in fingering:
#             num_fingering = fingerToNum(each_fingering)
#             if num_fingering not in dictionary:
#                 dictionary[num_fingering] = idx
#                 idx += 1
#     reverse_dictionary = dict(zip(dictionary.values(), dictionary.keys()))
#     return dictionary, reverse_dictionary

# dictionary, reverse_dictionary = build_dataset(finger_up)
# vocab_size: number of fingering

# def generateNewState(state, finger_pred, new_interval):
#     middle = state[1]
#     first = 0
#     if abs(middle) < 10:
#         first = abs(middle) + 300
#     if abs(middle) > 10:
#         # output is int
#         first = abs(middle)%10 + 300
#     middle_new = int(str(state[2] - 200) + str(finger_pred - 300))
#     last = new_interval + 200
#     return [first, middle_new, last]

def generateNewState(state, finger_pred, new_interval):
    return state[2:]+[finger_pred, new_interval]

# def ouputDecode(state):

vocab_size = 5

test_interval, first_input = getTestData()

# Parameters
learning_rate = 0.001
training_iters = 50000
display_step = 1000
n_input = 8
n_phrase = len(input_list)

# number of units in RNN cell
n_hidden = 256

# tf Graph input
x = tf.placeholder("float", [None, n_input, 1])
y = tf.placeholder("float", [None, vocab_size])

# RNN output node weights and biases
weights = {
    'out': tf.Variable(tf.random_normal([n_hidden, vocab_size]))
}
biases = {
    'out': tf.Variable(tf.random_normal([vocab_size]))
}

def RNN(x, weights, biases):

    # reshape to [1, n_input]
    x = tf.reshape(x, [-1, n_input])

    # Generate a n_input-element sequence of inputs
    # (eg. [had] [a] [general] -> [20] [6] [33])
    x = tf.split(x,n_input,1)

    # 2-layer LSTM, each layer has n_hidden units.
    # Average Accuracy= 95.20% at 50k iter
    rnn_cell = rnn.MultiRNNCell([rnn.BasicLSTMCell(n_hidden),rnn.BasicLSTMCell(n_hidden)])

    # 1-layer LSTM with n_hidden units but with lower accuracy.
    # Average Accuracy= 90.60% 50k iter
    # Uncomment line below to test but comment out the 2-layer rnn.MultiRNNCell above
    # rnn_cell = rnn.BasicLSTMCell(n_hidden)

    # generate prediction
    outputs, states = rnn.static_rnn(rnn_cell, x, dtype=tf.float32)

    # there are n_input outputs but
    # we only want the last output
    return tf.matmul(outputs[-1], weights['out']) + biases['out']

pred = RNN(x, weights, biases)

# Loss and optimizer
cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=pred, labels=y))
optimizer = tf.train.RMSPropOptimizer(learning_rate=learning_rate).minimize(cost)

# Model evaluation
correct_pred = tf.equal(tf.argmax(pred,1), tf.argmax(y,1))
accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))

# Initializing the variables
init = tf.global_variables_initializer()
# saver = tf.train.Saver()
# Launch the graph
with tf.Session() as session:
    session.run(init)
    step = 0
    offset = 0
    acc_total = 0
    loss_total = 0
    generate_step = len(test_interval) - 2

    writer.add_graph(session.graph)

    while step < training_iters:
        # Generate a minibatch. Add some randomness on selection process.
        if offset+1 >= n_phrase:
            offset = 0
            
        symbols_in_keys = input_list[offset]
        symbols_in_keys = np.reshape(np.array(symbols_in_keys), [-1, n_input, 1])

        symbols_out_onehot = np.zeros([vocab_size], dtype=float)
        symbols_out_onehot[label_list[offset]-1] = 1.0
        symbols_out_onehot = np.reshape(symbols_out_onehot,[1,-1])

        _, acc, loss, onehot_pred = session.run([optimizer, accuracy, cost, pred], \
                                                feed_dict={x: symbols_in_keys, y: symbols_out_onehot})
        loss_total += loss
        acc_total += acc
        if (step+1) % display_step == 0:
            print("Iter= " + str(step+1) + ", Average Loss= " + \
                  "{:.6f}".format(loss_total/display_step) + ", Average Accuracy= " + \
                  "{:.2f}%".format(100*acc_total/display_step))
            acc_total = 0
            loss_total = 0
            symbols_in = input_list[offset]
            symbols_out = label_list[offset]
            symbols_out_pred = int(tf.argmax(onehot_pred, 1).eval())+1
            print("%s - [%s] vs [%s]" % (symbols_in,symbols_out,symbols_out_pred))
        # if step > 49900:
        #     symbols_in = input_list[offset]
        #     symbols_out = label_list[offset]
        #     symbols_out_pred = int(tf.argmax(onehot_pred, 1).eval())+1
        #     print("%s - [%s] vs [%s]" % (symbols_in,symbols_out,symbols_out_pred))
        step += 1
        offset += 1
    # saver.save(session, "/Model/model.ckpt") 
    test_finger = [1,2,3,5,3,1,2,3,5,2,1,1,1,3,4,3,2,1,2]
    interval_test = test_interval[0:len(test_finger)]
    init_state = [1,test_interval[0],2,test_interval[1],3,test_interval[2],5,test_interval[3]]
    test_step = 0
    generate_step = len(test_finger)
    while test_step < generate_step:
        np_init_state = np.reshape(np.array(init_state), [-1, n_input, 1])
        onehot_pred_test = session.run(pred, feed_dict={x: np_init_state})
        finger_pred = int(tf.argmax(onehot_pred_test, 1).eval())+1
        print(str(init_state) + "->" + str(finger_pred))
        init_state = init_state[2:] + [test_finger[test_step+4],test_interval[test_step+4]]
        test_step+=1
    # test_step = 0
    # init_state = first_input
    # while test_step < generate_step:
    #     np_init_state = np.reshape(np.array(init_state), [-1, n_input, 1])
    #     onehot_pred_test = session.run(pred, feed_dict={x: np_init_state})
    #     finger_pred = int(tf.argmax(onehot_pred_test, 1).eval())+1
    #     print(str(init_state) + "->" + str(finger_pred))
    #     init_state = generateNewState(init_state, finger_pred, test_interval[test_step+2])
    #     test_step += 1
    print("Optimization Finished!")
    print("Elapsed time: ", elapsed(time.time() - start_time))
    print("Run on command line.")
    print("\ttensorboard --logdir=%s" % (logs_path))
    print("Point your web browser to: http://localhost:6006/")



    # while True:
    #     prompt = "%s words: " % n_input
    #     sentence = input(prompt)
    #     sentence = sentence.strip()
    #     words = sentence.split(' ')
    #     if len(words) != n_input:
    #         continue
    #     try:
    #         symbols_in_keys = [dictionary[str(words[i])] for i in range(len(words))]
    #         for i in range(32):
    #             keys = np.reshape(np.array(symbols_in_keys), [-1, n_input, 1])
    #             onehot_pred = session.run(pred, feed_dict={x: keys})
    #             onehot_pred_index = int(tf.argmax(onehot_pred, 1).eval())
    #             sentence = "%s %s" % (sentence,reverse_dictionary[onehot_pred_index])
    #             symbols_in_keys = symbols_in_keys[1:]
    #             symbols_in_keys.append(onehot_pred_index)
    #         print(sentence)
    #     except:
    #         print("Word not in dictionary")