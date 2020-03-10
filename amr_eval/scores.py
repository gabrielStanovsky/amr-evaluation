#!/usr/bin/env python
#coding=utf-8

'''
Computes AMR scores for concept identification, named entity recognition, wikification,
negation detection, reentrancy detection and SRL.

@author: Marco Damonte (m.damonte@sms.ed.ac.uk)
@since: 03-10-16
'''

import sys
import amr_eval.smatch.amr as amr
import amr_eval.smatch.smatch_fromlists as smatch
from pprint import pprint
from collections import defaultdict
import logging
import pdb
from amr_eval.utils import *

def get_operation_classification(triples, var_dict):
    """
    Get a mapping from textual element to operation type encoded in the input
    AMR.
    """
    # Find all operations classifications by the "-enum" suffix
    op_dict = dict([(var_name, operation_type)
                    for (var_name, operation_type)
                    in var_dict.items()
                    if operation_type.endswith("-enum")])

    # Find name mappings
    name_maps = {}
    for (rel, var, val) in triples:
        if (rel in ["op1", "name"]):
            name_maps[var] = val

    # Traverse relations to find the classification
    # of operations
    op_class_map = {}
    for (var, op_class) in op_dict.items():
        op_name = name_maps[name_maps[var]]
        if op_name != "event_":
            # Only include explicit events
            op_class_map[op_name] = op_class

    return op_class_map



def calc_metrics(pred, gold):
    """
    Calculate agreement metrics for given predicted and gold AMRs.
    """

    inters = defaultdict(int)
    golds = defaultdict(int)
    preds = defaultdict(int)
    reentrancies_pred = []
    reentrancies_gold = []
    srl_pred = []
    srl_gold = []

    k = 0
    tot = 0
    correct = 0
    for amr_pred, amr_gold in zip(pred, gold):
        amr_pred = amr.AMR.parse_AMR_line(amr_pred.replace("\n","")) 
        dict_pred = var2concept(amr_pred)
        triples_pred = []
        for t in amr_pred.get_triples()[1] + amr_pred.get_triples()[2]:
            if t[0].endswith('-of'):
                triples_pred.append((t[0][:-3], t[2], t[1]))
            else:
                triples_pred.append((t[0], t[1], t[2]))

        amr_gold = amr.AMR.parse_AMR_line(amr_gold.replace("\n",""))
        dict_gold = var2concept(amr_gold)
        triples_gold = []
        for t in amr_gold.get_triples()[1] + amr_gold.get_triples()[2]:
            if t[0].endswith('-of'):
                triples_gold.append((t[0][:-3], t[2], t[1]))
            else:
                triples_gold.append((t[0], t[1], t[2]))

        list_pred = disambig(concepts(dict_pred))
        list_gold = disambig(concepts(dict_gold))
        inters["Concepts"] += len(list(set(list_pred) & set(list_gold)))
        preds["Concepts"] += len(set(list_pred))
        golds["Concepts"] += len(set(list_gold))
        list_pred = disambig(namedent(dict_pred, triples_pred))
        list_gold = disambig(namedent(dict_gold, triples_gold))
        inters["Named Ent."] += len(list(set(list_pred) & set(list_gold)))
        preds["Named Ent."] += len(set(list_pred))
        golds["Named Ent."] += len(set(list_gold))
        list_pred = disambig(negations(dict_pred, triples_pred))
        list_gold = disambig(negations(dict_gold, triples_gold))
        inters["Negations"] += len(list(set(list_pred) & set(list_gold)))
        preds["Negations"] += len(set(list_pred))
        golds["Negations"] += len(set(list_gold))

        list_pred = disambig(wikification(triples_pred))
        list_gold = disambig(wikification(triples_gold))
        inters["Wikification"] += len(list(set(list_pred) & set(list_gold)))
        preds["Wikification"] += len(set(list_pred))
        golds["Wikification"] += len(set(list_gold))

        reentrancies_pred.append(reentrancies(dict_pred, triples_pred))
        reentrancies_gold.append(reentrancies(dict_gold, triples_gold))

        srl_pred.append(srl(dict_pred, triples_pred))
        srl_gold.append(srl(dict_gold, triples_gold))

        # Operation classification accuracy
        op_class_pred = get_operation_classification(triples_pred, dict_pred)
        op_class_gold = get_operation_classification(triples_gold, dict_gold)

        # Find lexical triggers shared by both gold and pred
        shared_event_triggers = op_class_pred.keys() & op_class_gold.keys()
        num_of_triggers = len(shared_event_triggers)
        pred_shared_items = [(k, op_class_pred[k]) for k in shared_event_triggers]
        gold_shared_items = [(k, op_class_gold[k]) for k in shared_event_triggers]

        # TODO: A subtle point here is regarding what happens if there's
        # the same event, classification tuple appears more than once?
        op_class_intersection = set(pred_shared_items) & set(gold_shared_items)
        inters["op_class"] +=  len(op_class_intersection)

        # TODO: this is inherently symmetrical?
        preds["op_class"] += num_of_triggers
        golds["op_class"] += num_of_triggers


    scores = defaultdict(dict)

    for score in preds:
        if preds[score] > 0:
            pr = inters[score]/float(preds[score])
        else:
            pr = -1
        if golds[score] > 0:
            rc = inters[score]/float(golds[score])
        else:
            rc = -1
        if pr + rc > 0:
            f = 2*(pr*rc)/(pr+rc)
            logging.debug (score, '-> P:', "{0:.2f}".format(pr), ', R:', "{0:.2f}".format(rc), ', F:', "{0:.2f}".format(f))
        else:
            f = -1
            logging.debug (score, '-> P:', "{0:.2f}".format(pr), ', R:', "{0:.2f}".format(rc), ', F: 0.00')
        total_annots = preds[score] + golds[score]
        scores[score] = {"p": pr,
                         "r": rc,
                         "f1": f,
                         "total": total_annots}

    pr, rc, f = smatch.main(reentrancies_pred, reentrancies_gold, True)
    if ((len(reentrancies_pred) != 1) or (len(reentrancies_gold) != 1)):
        pdb.set_trace()
        raise Exception

    total_reentrancies = len(reentrancies_pred[0][0]) + len(reentrancies_gold[0][0])

    logging.debug ('Reentrancies -> P:', "{0:.2f}".format(float(pr)), ', R:', "{0:.2f}".format(float(rc)), ', F:', "{0:.2f}".format(float(f)))
    scores["Reentrancies"] = {"p": pr,
                              "r": rc,
                              "f1": f,
                              "total": total_reentrancies}

    pr, rc, f = smatch.main(srl_pred, srl_gold, True)
    if ((len(srl_pred) != 1) or (len(srl_gold) != 1)):
        pdb.set_trace()
        raise Exception

    total_srl = len(srl_pred[0][0]) + len(srl_gold[0][0])

    logging.debug ('SRL -> P:', "{0:.2f}".format(float(pr)), ', R:', "{0:.2f}".format(float(rc)), ', F:', "{0:.2f}".format(float(f)))
    scores["SRL"] = {"p": pr,
                     "r": rc,
                     "f1": f,
                     "total": total_srl}

    scores = dict(scores)
    return scores

if __name__ == "__main__":
    pred = open(sys.argv[1]).read().strip().split("\n\n")
    gold = open(sys.argv[2]).read().strip().split("\n\n")
    scores = calc_metrics(pred, gold)
    plogging.debug(scores)

