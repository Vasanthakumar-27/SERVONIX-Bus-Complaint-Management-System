# Contributing to SERVONIX

Thank you for your interest in contributing to SERVONIX! We welcome contributions from everyone. This document provides guidelines and instructions for contributing.

## 🤝 How to Contribute

### 1. Fork & Clone
```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/SERVONIX-Bus-Complaint-Management-System.git
cd SERVONIX-Bus-Complaint-Management-System
```

### 2. Create a Feature Branch
```bash
git checkout -b feature/YourFeatureName
# or for bug fixes:
git checkout -b fix/YourBugFixName
```

### 3. Make Changes
- Follow the existing code style and structure
- Write clear, descriptive commit messages
- Test your changes thoroughly
- Update documentation if needed

### 4. Commit & Push
```bash
git add .
git commit -m "Add: Brief description of your changes"
git push origin feature/YourFeatureName
```

### 5. Create a Pull Request
- Go to the original repository
- Create a Pull Request from your branch
- Provide a clear description of changes
- Link any related issues

## 📋 Contribution Guidelines

### Code Style
- **Python**: Follow PEP 8 standards
- **JavaScript**: Use consistent indentation (2 spaces), camelCase for variables
- **HTML/CSS**: Use semantic HTML5 and CSS3 best practices

### Commit Messages
```
Type: Brief description (50 chars max)

Detailed explanation of changes (if needed)

Fixes #IssueNumber (if applicable)
```

**Types**: feat, fix, docs, style, refactor, test, chore

### Testing
Before submitting a PR:
- Test all new features thoroughly
- Run `python test_websocket.py` to verify API health
- Check browser console for JavaScript errors
- Test on multiple browsers/devices if UI changes

## 🎯 Areas for Contribution

### High Priority
- [ ] SMS notifications (Twilio integration)
- [ ] Mobile app (React Native)
- [ ] Advanced analytics dashboard
- [ ] Multi-language support (i18n)

### Medium Priority
- [ ] Export to Excel/PDF
- [ ] AI-based auto-categorization
- [ ] Performance optimization
- [ ] Additional authentication methods

### Low Priority
- [ ] UI theme improvements
- [ ] Documentation translation
- [ ] Additional test coverage
- [ ] Code refactoring

## 🐛 Reporting Bugs

Found a bug? Please report it:

1. **Check existing issues** - Avoid duplicates
2. **Create an issue** with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots/logs if applicable
   - Python/JavaScript version and browser info

## ❓ Questions?

- Check the [Documentation](./docs)
- Review existing [Issues](https://github.com/Vasanthakumar-27/SERVONIX-Bus-Complaint-Management-System/issues)
- Email: 927624bad117@mkce.ac.in

## 📝 Code of Conduct

### Our Pledge
We are committed to providing a welcoming and inclusive environment for all contributors.

### Expected Behavior
- Be respectful and inclusive
- Accept constructive criticism
- Focus on what's best for the community
- Show empathy towards others

### Unacceptable Behavior
- Harassment or discrimination
- Trolling or insulting comments
- Personal attacks
- Any form of abuse

## ✅ Pull Request Process

1. **Update documentation** for new features
2. **Add tests** if applicable
3. **Update CHANGELOG** if provided
4. **Ensure all checks pass** before PR
5. **One approval** required before merge
6. **Squash commits** for cleaner history (if requested)

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for making SERVONIX better!** 🎉

Every contribution counts, from code to documentation to bug reports.
