# Logical Errors and Fixes in app_sqlite.py

## Issues Identified:
1. **Timezone mismatch in OTP verification** - UTC vs local time comparison
2. **Datetime parsing errors** - `fromisoformat()` on non-ISO SQLite timestamps
3. **Inconsistent timestamp formatting** - Some use format_timestamp, others don't
4. **Incomplete media cleanup** - User deletion doesn't remove media files
5. **Inconsistent time windows** - Feedback (3min) vs complaints (5min)
6. **Missing file save verification** - Media upload doesn't check save success
7. **Inconsistent datetime usage** - Mixed localtime vs UTC usage

## Fixes to Implement:
- [ ] Fix OTP verification timezone issues
- [ ] Correct datetime parsing in user complaint listing
- [ ] Ensure consistent timestamp formatting
- [ ] Add media file cleanup in user complaint deletion
- [ ] Standardize time windows to 5 minutes
- [ ] Add file save success verification in media upload
- [ ] Ensure consistent datetime format usage throughout
