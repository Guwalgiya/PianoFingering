import intervalBook.wrong_combo as wrong_combo
import intervalBook.valid_combo as valid_combo

def main(interval_list, predicted_fingers, Gt_fingers):
    
    num_abs_true                     =  0
    num_abs_false                    =  0
    num_not_good                     =  0
    # predicted_fingers & Gt_fingers have one more element than interval_list does
    for i in range(len(interval_list)-1):
        if  predicted_fingers[i + 1] == Gt_fingers[i + 1]:
            num_abs_true             += 1
        else:
            num_abs_false            += sanityCheck (interval_list[i],  (predicted_fingers[i], predicted_fingers[i + 1]))
            num_not_good             += qualityCheck(interval_list[i], (predicted_fingers[i], predicted_fingers[i + 1]))
    return num_abs_true, num_abs_false

def sanityCheck(current_interval, current_finger_combo):
    if current_interval > 0:
        return (current_finger_combo in wrong_combo["up"])
    elif current_interval < 0:
        return (current_finger_combo in wrong_combo["down"])
    else:
        return False

def qualityCheck(current_interval, current_finger_combo):
    return (current_finger_combo not in valid_combo[current_interval])