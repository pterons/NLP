# -*- coding: utf-8 -*-
"""7-14.news_group20(transformer).ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/16jBabTVhXgblqxN3cG3iY50q_Twg8krC
"""

# Commented out IPython magic to ensure Python compatibility.
# %pip install sentencepiece

# Commented out IPython magic to ensure Python compatibility.
import numpy as np
import re
import pickle
from sklearn.datasets import fetch_20newsgroups
import sentencepiece as spm

from tensorflow.keras.layers import Input, Dense, GlobalAveragePooling1D
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import Model
import tensorflow.keras.backend as K
from tensorflow.keras import optimizers
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import seaborn as sns

# %cd '/content/drive/MyDrive/Colab Notebooks/삼성멀캠/자연어처리/7.챗봇_번역'
from transformer import Encoder, Decoder, PaddingMask

# news data를 읽어온다.
newsData = fetch_20newsgroups(shuffle=True, random_state=1, remove=('footers', 'quotes'))

news = newsData['data']
topic = newsData['target']
n_topic = len(set(topic))

# Subject만 추출한다.
subjects = []
y_topic = []
for text, top in zip(news, topic):
    for sent in text.split('\n'):
        idx = sent.find('Subject:')
        if idx >= 0:       # found
            subject = sent[(idx + 9):].replace('Re: ', '').lower()
            subject = re.sub("[^a-zA-Z]", " ", subject)
            if len(subject.split()) > 3:  # subject가 3단어 이상인 것만 허용한다.
                subjects.append(subject)
                y_topic.append(top)
            break

# Commented out IPython magic to ensure Python compatibility.
# Sentencepice용 사전을 만들기 위해 데이터를 저장해 둔다.
# %cd '/content/drive/MyDrive/Colab Notebooks'

data_file = "data/news_subject.txt"
with open(data_file, 'w', encoding='utf-8') as f:
    for sent in subjects:
        f.write(sent + '\n')

# Google의 Sentencepiece를 이용해서 vocabulary를 생성한다.
# -----------------------------------------------------
templates= "--input={0:} \
            --pad_id=0 --pad_piece=<PAD>\
            --unk_id=1 --unk_piece=<UNK>\
            --bos_id=2 --bos_piece=<START>\
            --eos_id=3 --eos_piece=<END>\
            --model_prefix={1:} \
            --vocab_size={2:} \
            --character_coverage=0.9995 \
            --model_type=unigram"

VOCAB_SIZE = 3000
model_prefix = "data/news_subject"
params = templates.format(data_file, model_prefix, VOCAB_SIZE)

spm.SentencePieceTrainer.Train(params)
sp = spm.SentencePieceProcessor()
sp.Load(model_prefix + '.model')

with open(model_prefix + '.vocab', encoding='utf-8') as f:
    vocab = [doc.strip().split('\t') for doc in f]

word2idx = {k:v for v, [k, _] in enumerate(vocab)}

# word index로 변환한다.
subject_idx = [sp.encode_as_ids(s) for s in subjects]

subject_len = [len(x) for x in subject_idx]
print('max = ', np.max(subject_len))
sns.displot(subject_len)

# 문장 길이를 맞추고, 학습 데이터를 생성한다.
x_data = pad_sequences(subject_idx, maxlen=30, padding='post', truncating='post')
y_data = y_topic

# 학습 데이터와 시험데이터로 분리한다.
x_train, x_test, y_train, y_test = train_test_split(x_data, y_data, test_size=0.1)
y_train = np.array(y_train).reshape(-1, 1)
y_test = np.array(y_test).reshape(-1, 1)

x_train.shape, y_train.shape, x_test.shape, y_test.shape

# Model
# -----
K.clear_session()
x_input = Input(batch_shape=(None, x_train.shape[1]), dtype="int32")

# Encoder
padding_mask = PaddingMask()(x_input)
encoder = Encoder(num_layers=2, d_model=64, num_heads=4, d_ff=32, vocab_size=len(word2idx), dropout_rate=0.5)
enc_output, _ = encoder(x_input, padding_mask)
enc_output = GlobalAveragePooling1D()(enc_output)

# FFN
y_output = Dense(n_topic, activation='softmax')(enc_output)

model = Model(inputs=x_input, outputs=y_output)
model.compile(optimizer=optimizers.Adam(learning_rate=0.0005), loss='sparse_categorical_crossentropy')
model.summary()

# 모델을 학습한다.
hist = model.fit(x_train, y_train, validation_data = (x_test, y_test), batch_size = 512, epochs = 30)

# Loss history를 그린다
plt.plot(hist.history['loss'], label='Train loss')
plt.plot(hist.history['val_loss'], label = 'Test loss')
plt.legend()
plt.title("Loss history")
plt.xlabel("epoch")
plt.ylabel("loss")
plt.show()

# 시험 데이터로 학습 성능을 평가한다
pred = model.predict(x_test)
y_pred = np.argmax(pred, axis=1).reshape(-1, 1)
accuracy = (y_pred == y_test).mean()
print("\nAccuracy = %.2f %s" % (accuracy * 100, '%'))

# 잘못 분류한 문장을 육안으로 확인해 본다.
mis_match = x_test[np.where(y_pred.reshape(-1) != y_test.reshape(-1))]

for n, m in enumerate(mis_match[:30]):
    # pad 제거
    idx = [int(i) for i in m if i != 0]
    print(n, ':', sp.decode_ids(idx))

