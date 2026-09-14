{
	"patcher": {
		"patching_rect": [0, 0, 800, 500],
		"boxes": [
			{
				"box": {
					"id": "obj-1",
					"maxclass": "newobj",
					"text": "udpreceive 9090",
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [""],
					"patching_rect": [50, 50, 120, 23],
					"comment": "OSCreceive equivalent for raw OSC - use in a Max for Live device or standalone patch"
				}
			},
			{
				"box": {
					"id": "obj-2",
					"maxclass": "newobj",
					"text": " Tigersniff /density /churn /proximity /band_balance /rf_warmth",
					"numinlets": 1,
					"numoutlets": 6,
					"outlettype": ["", "", "", "", "", ""],
					"patching_rect": [50, 100, 300, 23],
					"comment": "route OSC addresses -> change their name to 'Tigersniff OSCRoute' if using the OSC extras"
				}
			},
			{
				"box": {
					"id": "obj-3",
					"maxclass": "newobj",
					"text": "OSC-route /density /churn /proximity /band_balance /rf_warmth",
					"numinlets": 1,
					"numoutlets": 6,
					"outlettype": ["", "", "", "", "", ""],
					"patching_rect": [50, 100, 300, 23],
					"comment": "expected addresses from python osc_bridge.py"
				}
			},
			{
				"box": {
					"id": "obj-4",
					"maxclass": "comment",
					"text": "Mapping ideas (PLAN Phase 3):\n- /proximity  -> volume / filter cutoff sweep\n- /churn      -> bitcrush depth / transient artifacts\n- /density    -> delay feedback, granular glitch rate\n- /rf_warmth  -> pitch drift\n\nPipe the values through 'mute'/'tremol' or scale + live.remote for sidechain-free automation and you can play the crowd.",
					"patching_rect": [400, 150, 360, 160]
				}
			}
		],
		"lines": [
			{
				"patchline": {
					"source": ["obj-1", 0],
					"destination": ["obj-3", 0]
				}
			}
		]
	}
}
