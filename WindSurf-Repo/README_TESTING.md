# BYOS Command Center - Local Testing

## 🚀 One-Click Setup

**Just double-click `START_BYOS.bat` and you're done!**

The script will automatically:
- ✅ Check for Python and Node.js
- 📦 Install all dependencies
- 🗄️ Set up the database
- 🚀 Start the backend server (port 8765)
- 🎨 Start the dashboard (port 4321)
- 🌐 Open your browser automatically

## 📋 System URLs

After running the setup, access:

- **📊 Dashboard**: http://localhost:4321
- **🔧 Backend API**: http://localhost:8765
- **📚 API Documentation**: http://localhost:8765/docs

## 🧪 Testing Checklist

Once the system is running, test these features:

### Dashboard Homepage
- [ ] System statistics display
- [ ] Service status indicators
- [ ] Recent activity feed
- [ ] Quick action buttons

### System Controls
- [ ] Feature toggles work
- [ ] Safety confirmations appear
- [ ] Settings save properly

### Monitoring
- [ ] Performance charts load
- [ ] Time range selectors work
- [ ] Resource usage displays

### Audit Logs
- [ ] Logs display correctly
- [ ] Search and filtering work
- [ ] Pagination functions

### API Endpoints
- [ ] All dashboard endpoints respond
- [ ] Data loads correctly
- [ ] Error handling works

## 🔧 Manual Control

If you need to run components separately:

```bash
# Backend only
python run_local_test.py

# Dashboard only
cd apps/dashboard && npm start

# Database setup only
python -c "from alembic.config import Config; from alembic import command; alembic_cfg = Config('alembic/alembic_dev.ini'); command.upgrade(alembic_cfg, 'head')"
```

## 🚨 Troubleshooting

**If something doesn't work:**

1. **Check the command windows** for error messages
2. **Wait a few seconds** - services need time to start
3. **Check ports** - make sure 4321 and 8765 are free
4. **Restart** - close all windows and run `START_BYOS.bat` again

**Port conflicts?**
Edit the scripts to change ports:
- Backend: `run_local_test.py` (line 16)
- Dashboard: `apps/dashboard/package.json` (start script)

## 📊 What You'll See

The dashboard provides:
- **Real-time system monitoring**
- **Safety-first system controls**
- **Complete audit trail**
- **Enterprise-grade features**
- **Childproof design** (no accidental disasters!)

## 🎯 Next Steps

After testing locally, you're ready for:
- Production deployment
- Custom branding
- API integrations
- Advanced configurations

**Enjoy exploring your BYOS Command Center!** 🎉
