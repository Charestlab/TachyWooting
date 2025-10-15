
from wooting_package import WOOTING_ACQUISITION, convert_char_to_keycode, lib, ffi
import time
import os

def wooting_plotting_response_test(target_key, reps=10):
    import matplotlib.pyplot as plt

    if not (isinstance(target_key, list) and len(target_key) == 1):
        raise ValueError("target_key must be a list of single character or integer for the test")

    try:
        acqui = WOOTING_ACQUISITION()
        acqui.initialize_keyboard()
        # integer logging + CSV juste pour l’exemple
        acqui.setup_logging(path=os.getcwd(), name="tracking.csv", int_analog=1, formats="csv")

        # (optionnel) sanity-check 2 secondes de lecture brute
        code = convert_char_to_keycode(target_key)[0] if isinstance(target_key[0], str) else target_key[0]
        print(f"[sanity] Reading analog for key {target_key[0]} (code {code}) for 2s… tape un peu la touche.")
        t0 = time.time()
        while time.time() - t0 < 2.0:
            val = lib.wooting_analog_read_analog(code)
            # affiche quelques valeurs
            if int((time.time() - t0) * 20) % 5 == 0:
                print(f"value={val:.3f}", end="\r")
            time.sleep(0.01)
        print()

        for i in range(reps):
            print(f"{i+1} : Press {target_key}")
            data = acqui.acquire_integer_values(
                duration_before_threshold=0.5,
                target_keys=target_key,
                threshold=26  # ~10% (26/255)
            )
            times = [d['time_to_threshold'] for d in data]
            positions = [d['position'] for d in data]
            plt.plot(times, positions, label=f'Trial {i+1}')

        plt.xlabel('Time to Threshold (s)')
        plt.ylabel('Position')
        plt.title('Key Response Over Time')
        plt.legend()
        plt.savefig("plot.png")
    finally:
        # 2) uninit SDK pour libérer et fusionner les logs éventuels
        acqui.uninitialize_keyboard()

    plt.xlabel('Time to Threshold (s)')
    plt.ylabel('Position')
    plt.title('Key Response Over Time')
    plt.legend()
    plt.savefig("plot.png")


wooting_plotting_response_test(['z'], 10)
