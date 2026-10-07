from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock

from galerazo_bot.database import Database
from galerazo_bot.final_boss import FinalBossStore
from galerazo_bot.final_boss_telegram import recover_boss_results, schedule_boss_recovery
from galerazo_bot.telegram_bot import _restore_hisopo_jobs


class FinalBossSchedulingTests(IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.db = Database(Path(temporary.name) / "scheduling.sqlite3")
        self.db.register_chat("-1", "group", "Fixture")
        self.jobs = MagicMock()
        self.jobs.get_jobs_by_name.return_value = ()
        self.application = SimpleNamespace(
            bot_data={"state": SimpleNamespace(db=self.db)}, job_queue=self.jobs,
        )
        self.context = SimpleNamespace(application=self.application)
        self.now = datetime.now(timezone.utc)

    def spawn(self, kind):
        return self.db.save_hisopo_spawn(
            "-1", "10", kind, 0, "message", self.now.isoformat(),
            (self.now + timedelta(hours=1)).isoformat(),
        )

    async def test_ordinary_hisopos_never_start_boss_recovery(self):
        _restore_hisopo_jobs(self.application)
        self.jobs.run_repeating.assert_not_called()
        self.spawn("common")
        _restore_hisopo_jobs(self.application)
        self.jobs.run_once.assert_called_once()
        self.jobs.run_repeating.assert_not_called()
        await recover_boss_results(self.context)
        self.assertEqual(self.db.get_hisopo_spawn("-1", "10").status, "active")
        self.jobs.run_repeating.assert_not_called()

    async def test_recovery_arms_once_and_stops_when_results_are_delivered(self):
        self.spawn("final_boss")
        _restore_hisopo_jobs(self.application)
        self.jobs.run_repeating.assert_called_once()
        store = FinalBossStore(self.db)
        self.assertIsNotNone(store.get("-1", "10"))
        job = MagicMock()
        self.jobs.get_jobs_by_name.side_effect = lambda name: (job,) if name == "boss-results" else ()
        schedule_boss_recovery(self.application)
        self.jobs.run_repeating.assert_called_once()
        await recover_boss_results(self.context)
        job.schedule_removal.assert_not_called()
        store.expire("-1", "10", self.now + timedelta(hours=2))
        await recover_boss_results(self.context)
        job.schedule_removal.assert_not_called()
        store.mark_announced("-1", "10", "20")
        store.complete_announcement("-1", "10")
        await recover_boss_results(self.context)
        job.schedule_removal.assert_called_once()

    async def test_restart_arms_pending_result_without_an_active_boss(self):
        self.spawn("final_boss")
        store = FinalBossStore(self.db)
        store.create("-1", "10", self.now, 0)
        store.expire("-1", "10", self.now + timedelta(hours=2))
        _restore_hisopo_jobs(self.application)
        self.jobs.run_repeating.assert_called_once()
        self.jobs.run_once.assert_not_called()
        await recover_boss_results(self.context)
        self.jobs.run_once.assert_called_once()
