from __future__ import annotations

import os
import random
import time

import numpy as np
from tachypy import ResponseHandler, Screen, Text, Texture

from wooting_package import WOOTING_ACQUISITION

N_TRIALS    = 20
YES_KEY     = "z"   # white response
NO_KEY      = "c"   # black response
WARN_STREAK = 2     # flag after this many consecutive removals
QUIT_KEYS   = {"escape", "esc", "enter", "return", "space", "q"}
BG          = (128, 128, 128)


def main() -> int:
    acq = WOOTING_ACQUISITION(threshold=0.80, light_press_hold_seconds=1,  min_pressure_start = 0.33, max_pressure_start = 0.66)
    acq.initialize_keyboard()

    screen = None
    try:
        screen = Screen(fullscreen=False)
        screen.hide_mouse()
        rh = ResponseHandler(screen=screen)
        rh.keys_to_listen = sorted(QUIT_KEYS)

        w, h = screen.width, screen.height
        margin = 16

        white_tex = Texture(np.ones((256, 256, 3), dtype=np.uint8) * 255)
        black_tex = Texture(np.zeros((256, 256, 3), dtype=np.uint8))

        label = Text(text=".", font_size=28, color=(0, 0, 0),
                     dest_rect=(0, margin, w, margin + 44))
        score = Text(text="Score: —", font_size=24, color=(0, 0, 0),
                     dest_rect=(w - 240, margin + 50, w - margin, margin + 122))

        yes_code, no_code = acq._to_keycodes([YES_KEY, NO_KEY])

        # --- instructions screen ---
        instructions = Text(
            text=(
                "Welcome!\n \n"
                "A black or white image will appear.\n"
                f"Press  {YES_KEY.upper()}  if it is white,  {NO_KEY.upper()}  if it is black.\n \n"
                f"Before each trial, rest your fingers lightly on {YES_KEY.upper()} and {NO_KEY.upper()}.\n"
                f"The trial starts as soon as the pressure is stable for {acq.hold_seconds} second(s).\n"
                "After your response, lift your fingers completely off the keys.\n \n"
                f"Press  {YES_KEY.upper()}  to begin."
            ),
            font_size=26,
            color=(0, 0, 0),
            dest_rect=(int(w * 0.1), int(h * 0.15), int(w * 0.9), int(h * 0.85)),
        )
        screen.fill(BG)
        instructions.draw()
        screen.flip()
        acq.wait_keys_light_press(target_keys=[YES_KEY], quit_key=NO_KEY)

        correct = clean = 0

        for trial in range(1, N_TRIALS + 1):
            is_white = bool(random.getrandbits(1))

            if not acq.wait_keys_light_press_visual(
                screen=screen,
                target_keys=[YES_KEY, NO_KEY],
                response_handler=rh,
                exit_keys=QUIT_KEYS,
                show_pressure_text=True,
                left_pressure_label=YES_KEY.upper(),
                right_pressure_label=NO_KEY.upper(),
            ):
                break

            screen.fill(BG)
            (white_tex if is_white else black_tex).draw(
                (w // 2 - 128, h // 2 - 128, w // 2 + 128, h // 2 + 128)
            )
            label.set_text(f"Trial {trial}/{N_TRIALS} | {YES_KEY.upper()} = white  {NO_KEY.upper()} = black")
            label.draw()
            score.draw()
            screen.flip()

            hier = acq.acquire_analog_values(target_keys=[YES_KEY, NO_KEY])
            response = acq.get_response_key(hier, target_keys=[YES_KEY, NO_KEY])

            is_correct = response == (yes_code if is_white else no_code)
            had_removal = acq.last_trial_had_removal
            correct += int(is_correct)
            clean += int(not had_removal)
            score.set_text(f"Correct:  {correct / trial * 100:.0f}%\nClean:    {clean / trial * 100:.0f}%")

            feedback = "Correct!" if is_correct else "Incorrect"
            if acq.reached_consecutive_removal_limit(WARN_STREAK):
                feedback += f"  [finger removal ×{acq.current_removal_streak}]"
            elif had_removal:
                feedback += "  [finger removal]"

            screen.fill(BG)
            label.set_text(feedback)
            label.draw()
            score.draw()
            screen.flip()
            time.sleep(0.75)

            if acq.wait_keys_released(
                target_keys=[YES_KEY, NO_KEY],
                response_handler=rh,
                exit_keys=QUIT_KEYS,
            ) is None:
                break

        print(f"Done — {correct}/{acq.total_trials} correct, {acq.removal_trials} removal trials")
        return 0

    finally:
        acq.uninitialize_keyboard()
        if screen is not None and hasattr(screen, "close"):
            screen.close()


if __name__ == "__main__":
    raise SystemExit(main())
