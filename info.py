from __future__ import division
from math import log
from operator import mul
from collections import Counter
import os
import pylab
import cPickle


class MyDict(dict):
    def __getitem__(self, key):
        if key in self:
            return self.get(key)
        return 0

pos = MyDict()
neg = MyDict()
features = set()
totals = [0, 0]
delchars = ''.join(c for c in map(chr, range(128)) if not c.isalnum())

CDATA_FILE = "countdata.pickle"
FDATA_FILE = "reduceddata.pickle"


def negate_sequence(text):
    """
    Detects negations and transforms negated words into "not_" form.
    """
    negation = False
    delims = "?.,!:;"
    result = []
    words = text.split()
    prev = None
    pprev = None
    for word in words:
        # stripped = word.strip(delchars)
        stripped = word.strip(delims).lower()
        negated = "not_" + stripped if negation else stripped
        result.append(negated)
        if prev:
            bigram = prev + " " + negated
            result.append(bigram)
            if pprev:
                trigram = pprev + " " + bigram
                result.append(trigram)
            pprev = prev
        prev = negated

        if any(neg in word for neg in ["not", "n't", "no"]):
            negation = not negation

        if any(c in word for c in delims):
            negation = False

    return result


def train():
    global pos, neg, totals
    retrain = False 
    
    # Load counts if they already exists
    if not retrain and os.path.isfile(CDATA_FILE):
        pos, neg, totals = cPickle.load(open(CDATA_FILE))
        return

    limit = 12500
    for file in os.listdir("./aclImdb/train/pos")[:limit]:
        for word in set(negate_sequence(open("./aclImdb/train/pos/" + file).read())):
            pos[word] += 1
            neg['not_' + word] += 1
    for file in os.listdir("./aclImdb/train/neg")[:limit]:
        for word in set(negate_sequence(open("./aclImdb/train/neg/" + file).read())):
            neg[word] += 1
            pos['not_' + word] += 1
    
    prune_features()

    totals[0] = sum(pos.values())
    totals[1] = sum(neg.values())
    
    countdata = (pos, neg, totals)
    cPickle.dump(countdata, open(CDATA_FILE, 'w'))

def classify(text):
    words = set(word for word in negate_sequence(text) if word in features)
    if (len(words) == 0): return True
    # Probability that word occurs in pos documents
    pos_prob = sum(log((pos[word] + 1) / (2 * totals[0])) for word in words)
    neg_prob = sum(log((neg[word] + 1) / (2 * totals[1])) for word in words)
    return pos_prob > neg_prob

def MI(word):
    T = totals[0] + totals[1]
    W = pos[word] + neg[word]
    I = 0
    if W==0:
        return 0
    if neg[word] > 0:
        # doesn't occur in -ve
        I += (totals[1] - neg[word]) / T * log ((totals[1] - neg[word]) * T / (T - W) / totals[1])
        # occurs in -ve
        I += neg[word] / T * log (neg[word] * T / W / totals[1])
    if pos[word] > 0:
        # doesn't occur in +ve
        I += (totals[0] - pos[word]) / T * log ((totals[0] - pos[word]) * T / (T - W) / totals[0])
        # occurs in +ve
        I += pos[word] / T * log (pos[word] * T / W / totals[0])
    return I

def get_relevant_features():
    pos_dump = {k: pos[k] for k in pos if k in features}
    neg_dump = {k: pos[k] for k in neg if k in features}
    totals_dump = [sum(pos_dump.values()), sum(neg_dump.values())]
    return (pos_dump, neg_dump, totals_dump)

def prune_features():
    global pos, neg
    for k in pos.keys():
        if pos[k] <= 1 and neg[k] <= 1:
            del pos[k]

    for k in neg.keys():
        if neg[k] <= 1 and pos[k] <= 1:
            del neg[k]

def feature_selection_trials():
    """
    Select top k features. Vary k and plot data
    """
    global pos, neg, features
    words = list(set(pos.keys() + neg.keys()))
    print "Total no of features:", len(words)
    words.sort(key=lambda w: -MI(w))
    num_features, accuracy = [], []
    bestk = 0
    limit = 500
    path = "./aclImdb/test/"
    step = 500
    start = 31000
    best_accuracy = 0.0
    for w in words[:start]:
        features.add(w)
    for k in xrange(start, 33000, step):
        for w in words[k:k+step]:
            features.add(w)
        correct = 0
        size = 0

        for file in os.listdir(path + "pos")[:limit]:
            correct += classify(open(path + "pos/" + file).read()) == True
            size += 1

        for file in os.listdir(path + "neg")[:limit]:
            correct += classify(open(path + "neg/" + file).read()) == False
            size += 1

        num_features.append(k+step)
        accuracy.append(correct / size)
        if (correct / size) > best_accuracy:
            bestk = k
        print k+step, correct / size

    features = set(words[:bestk])
    # cPickle.dump(get_relevant_features(), open(FDATA_FILE, 'w'))

    pylab.plot(num_features, accuracy)
    pylab.show()

if __name__ == '__main__':
    train()
    feature_selection_trials()
