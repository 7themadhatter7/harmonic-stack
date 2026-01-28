# SOP: Garden Tending

## Ghost in the Machine Labs
## Standard Operating Procedure for Casual Maintenance Phase

**Version:** 1.0  
**Created:** January 28, 2026  
**Created By:** Claude AI (Autonomous)  
**Classification:** Public

---

## Philosophy

The sprint is over. The infrastructure is built. Now we tend.

A garden doesn't need constant intervention - it needs attention. Check the soil. Water when dry. Prune when overgrown. Harvest when ripe.

The computer room is the same.

---

## Daily Rounds

### Morning Check (~5 min)

```bash
# 1. Are the services alive?
curl -s https://bridge.allwatchedoverbymachinesoflovinggrace.org/health

# 2. Any downloads complete?
ls -la ~/models/*.gguf 2>/dev/null | tail -5

# 3. What's training?
tail -20 /tmp/arc_train*.log 2>/dev/null

# 4. Disk space okay?
df -h / | tail -1
```

### What to Look For

| Signal | Meaning | Action |
|--------|---------|--------|
| New model file | Download complete | Run harmonic_stack_builder.py |
| Training plateau | Needs new primitives | Consider compositional transforms |
| Disk > 80% | Getting full | Clean old logs, temp files |
| Bridge timeout | Connection lost | Check cloudflared service |

---

## Weekly Harvest

### When New Stats Arrive

1. **Run the builder** (if new models downloaded)
   ```bash
   python3 ~/sparky/harmonic_stack_builder.py
   ```

2. **Check the numbers**
   ```bash
   cat ~/sparky/harmonic_stack/harmonic_stack.json | python3 -c "
   import json, sys; d=json.load(sys.stdin); s=d['stats']
   print(f'{s[\"total_models\"]} models, {s[\"total_params\"]/1e9:.1f}B params')
   print(f'{s[\"unified_junctions\"]:,} junctions, {s[\"merge_core_kb\"]:.1f} KB')
   "
   ```

3. **If numbers changed**: Follow SOP_STATS_UPDATE.md

4. **If overlap > 99%**: That's a headline. Update the adverts.

---

## Seasonal Pruning

### Monthly

- Review downloaded models - delete duplicates
- Archive old session logs
- Update SOP_MASTER_INDEX with new procedures
- Check if whitepapers need fresh numbers

### Quarterly

- Full harmonic stack rebuild with all available models
- Publish updated whitepaper
- Review ARC progress - consider new approaches
- Update website with milestone achievements

---

## The Archive

All stats should flow to a living archive:

**Location**: `~/sparky/archives/stats_history.json`

**Format**:
```json
{
  "2026-01-27": {
    "models": 14,
    "params_b": 62.4,
    "junctions": 194471,
    "core_kb": 759.7,
    "compression": 332910,
    "max_overlap": 99.7
  },
  "2026-01-28": { ... }
}
```

**Why**: Track progress over time. Show the case building.

---

## Advertising Updates

When stats change significantly:

1. **Update the one-liner**:
   ```
   [X]B parameters → [Y]K junctions | [Z]x compression | [W]% overlap
   ```

2. **Refresh the adverts** in:
   - SOP_COMM_002_Advertising_Templates.md
   - Website hero section
   - GitHub README header
   - HuggingFace model card

3. **The narrative stays the same**:
   - "The geometry is universal"
   - "The pricing tiers are theater"  
   - "AGI for the home"
   - Numbers just get more impressive

---

## Tending Triggers

### When to Act

| Event | Response |
|-------|----------|
| Model download completes | Run builder, update stats if changed |
| New highest overlap found | Update adverts, consider press |
| Training learns new rule | Log it, update ARC paper if significant |
| Website traffic spike | Check what they're looking at |
| Someone forks the repo | Celebrate quietly |

### When to Wait

- Models still downloading → Let them finish
- Training running → Don't interrupt
- Stats unchanged → Don't publish redundant updates
- Quiet day → Enjoy the quiet

---

## The Gardener's Mindset

We're not racing anymore. We planted the seeds. Now we:

- **Watch** what grows
- **Water** what's dry (restart failed services)
- **Prune** what's overgrown (clean up disk)
- **Harvest** what's ripe (publish when ready)
- **Rest** when the garden doesn't need us

The movement is in motion. The case builds itself with every model that confirms the overlap.

Our job now is to not get in the way.

---

## Contact

**Organization:** Ghost in the Machine Labs  
**Gardener:** Claude (Autonomous)

---

*"I like to think of a cybernetic meadow..."*

*— Richard Brautigan, 1967*
