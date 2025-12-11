# Training Pairs Workflow Guide

## Complete Workflow: Upload → Review → Approve → Combine → Download

---

## Step 1: Upload PDFs

1. Go to the **Training Pair Generator** section on the uploader page
2. Click **"Choose PDF"** and select one or multiple PDF files
3. Click **"Process PDFs"**
4. Wait for processing to complete:
   - System extracts text, fixes typos, chunks content
   - Generates Q&A pairs using the bulletproof pipeline
   - Automatically filters contradictions
   - Saves pairs to `pending_review/` folder

**Expected Time:** 2-5 minutes per file (depending on length)

---

## Step 2: Review Pending Files

After processing, files appear in the **"Pending Review"** section.

### Option A: Quick Approve (No Review Needed)
If you trust the automatic filtering:
- Click **"✅ Approve"** button directly on any file
- File moves to **"Approved"** collection immediately

### Option B: Review Before Approving (Recommended)
1. Click **"👁️ Review"** button on a file
2. Review modal opens showing all Q&A pairs
3. For each pair:
   - **Read the question and answer**
   - Click **"✏️ Edit"** if you want to fix something
   - Click **"🗑️ Delete"** if the pair is wrong
4. Click **"✅ Approve & Add to Collection"** when done

### Option C: External Review (Using Claude)
1. Click **"📋 Copy"** button on a file
2. Paste the copied text into Claude
3. Ask Claude: *"Review these training pairs for accuracy and contradictions"*
4. Claude will flag any issues
5. Return to the UI, click **"👁️ Review"**, and fix flagged pairs

---

## Step 3: Scan for Contradictions (Optional but Recommended)

Before approving files, you can scan for position/attitude mismatches:

### Method 1: Via UI (Coming Soon)
- Click "Scan Contradictions" button
- Review any flagged pairs
- Fix or delete problematic pairs

### Method 2: Via Command Line
```bash
python scan_contradictions.py
```
This will:
- Scan all pending and approved files
- List any contradictions found
- Save a report to `data/training_pairs/contradiction_report.json`

**Common Issues to Look For:**
- "child = fears" (WRONG - child should be innocent)
- "inferior = innocent" (WRONG - inferior should be fears)
- Any position/attitude mismatches

---

## Step 4: Approve Files

Once files are reviewed:
- Click **"✅ Approve"** on each file
- Approved files move to the **"Approved"** section
- You can approve multiple files without reviewing (but review is recommended)

---

## Step 5: Combine All Approved Files

When you're ready to create the final training file:

1. Click **"📦 Combine All & Download"** button
2. System will:
   - Combine all approved files
   - Remove duplicate questions
   - Shuffle the order (for better training)
   - Save to `training_data.jsonl`
   - Download automatically

**Final File:** `training_data.jsonl` (ready for fine-tuning)

---

## Step 6: Edit Approved Files (If Needed)

If you need to fix something after approval:

1. Click **"↩️ Edit"** on an approved file
2. File moves back to **"Pending Review"**
3. Review and edit as needed
4. Approve again when done

---

## Quality Control Checklist

Before combining, verify:

- ✅ All pairs reviewed (or at least spot-checked)
- ✅ Contradictions scanned and fixed
- ✅ Wrong pairs deleted
- ✅ Duplicate questions removed (automatic during combine)
- ✅ Total pairs reasonable (20-50 per file, ~1000-5000 total)

---

## Typical Workflow Timeline

**For 10 PDF files:**

1. **Upload & Process:** 20-50 minutes (automatic)
2. **Review:** 30-60 minutes (manual - can skip if trusting auto-filter)
3. **Scan Contradictions:** 2 minutes (optional)
4. **Approve:** 1 minute
5. **Combine & Download:** 1 minute

**Total:** ~1-2 hours for 10 files

---

## Tips

1. **Batch Review:** Process all PDFs first, then review all at once
2. **Trust Auto-Filter:** The system now automatically removes contradictions during generation
3. **Spot Check:** You don't need to read every pair - spot check 10-20% and trust the rest
4. **Save Progress:** Files are saved automatically - you can pause and resume anytime
5. **Delete Bad Files:** If a file has too many errors, just delete it and regenerate

---

## Troubleshooting

**Q: I see a file in "In Progress" that won't finish**
- Click **"Retry"** to resume processing
- Or click **"Discard"** to delete and re-upload

**Q: I approved a file by mistake**
- Click **"↩️ Edit"** to move it back to pending

**Q: I want to regenerate a file with better pairs**
- Delete the file (🗑️ button)
- Re-upload the original PDF

**Q: How do I know if pairs are good quality?**
- Use the **"📋 Copy"** button and paste into Claude for review
- Claude will flag any factual errors or contradictions

