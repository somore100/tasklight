DEFAULTS = {
    # hotkeys
    "hk_quit":          "f9",
    "hk_record":        "f6",
    "hk_play":          "f7",
    "hk_stop":          "f8",
    "hk_jitter_solo":   "f1",
    "hk_clicker_solo":  "f2",
    "hk_net_blocker":   "f3",
    "hk_dup_solo":      "f4",

    # playback
    "speed":    "1.0",
    "loops":    "1",
    "infinite": False,

    # human mode
    "human_enabled":        False,
    "delay_addon":          True,
    "delay_min":            "0.01",
    "delay_max":            "0.05",
    "smooth_addon":         True,
    "smooth_steps":         "8",
    "jitter_addon":         True,
    "jitter_px":            "3",
    "jitter_max":           "8",
    "jitter_aggression":    "5",
    "clicker_addon":        True,
    "clicker_cps_base":     "13",
    "clicker_cps_loss":     "3",
    "clicker_cps_min":      "5",
    "clicker_cps_max":      "30",
    "clicker_hold_min":     "0.02",
    "clicker_hold_max":     "0.08",
    "clicker_burst_chance": "0.12",
    "clicker_burst_min":    "0.08",
    "clicker_burst_max":    "0.25",
    "clicker_slip_chance":  "0.03",

    # click duplicator
    "dup_enabled":    False,
    "dup_addon":      True,
    "dup_solo":       False,
    "dup_count":      "1",
    "dup_gap_ms":     "80",
    "dup_mode":       "random",
    "dup_use_jitter": False,

    # fps monitor
    "fps_enabled":    False,
    "fps_prefer_gpu": True,
    "fps_show_mini":  True,
    "fps_region":     None,

    # system monitor
    "sysmon_enabled":    False,
    "sysmon_interval":   "1.0",
    "sysmon_show_cpu":   True,
    "sysmon_show_ram":   True,
    "sysmon_show_gpu":   True,
    "sysmon_show_disk":  False,
    "sysmon_show_net":   False,
    "sysmon_show_temp":  False,
    "sysmon_show_mini":  True,
    "sysmon_show_cores": False,

    # UI
    "theme":          "dark",
    "layout":         "horizontal",
    "mini_mode":      False,
    "always_on_top":  True,
    "failsafe":       False,
    "wayland_banner": True,

    # section collapse
    "sec_playback":   True,
    "sec_human":      True,
    "sec_presets":    True,
    "sec_keybinds":   True,
    "sec_network":    True,
    "sec_sysmon":     True,

    # presets
    "preset_mode":      "simple",
    "preset_folder":    "",
    "auto_load_preset": "",
    "presets":          {},

    # clicker/duplicator buttons
    "clicker_button":   "left",   # "left" | "right" | "both"
    "dup_button":       "same",   # "same" | "left" | "right" | "both"

    # network
    "net_iface":          "",
    "net_ping_host":      "8.8.8.8",
    "net_show_mini_ping": True,
}
