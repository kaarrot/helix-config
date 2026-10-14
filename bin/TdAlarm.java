// td's reminder alarm: one exact Android alarm, owned by com.termux, that
// makes Termux run `td-tick --alarm`. `td install` builds this into
// ~/.cache/td/td-alarm.jar; td runs it under /system/bin/app_process as the
// Termux uid (the way $PREFIX/bin/am runs), so it talks to the activity and
// alarm services directly. Termux targets SDK 28, so Android 12 asks for no
// exact-alarm permission.
//
//   TdAlarm set SHIM EPOCH_MS   arm (replaces the previous alarm)
//   TdAlarm cancel SHIM         disarm
//
// The alarm is the quiet kind (setExactAndAllowWhileIdle: no status-bar
// icon). 15 s before it, a second alarm makes Termux take its wake lock, so
// the phone stays awake while the tick posts the notification; the tick
// releases it (`--alarm`).

import android.app.PendingIntent;
import android.content.Intent;
import android.net.Uri;
import android.os.IBinder;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;

public class TdAlarm {
    static final String PKG = "com.termux";
    static final String SERVICE = "com.termux.app.TermuxService";

    // ActivityManager.INTENT_SENDER_FOREGROUND_SERVICE
    static final int SENDER_FOREGROUND_SERVICE = 5;
    // PendingIntent.FLAG_*
    static final int UPDATE_CURRENT = 0x08000000, IMMUTABLE = 0x04000000,
            NO_CREATE = 0x20000000;
    // AlarmManager.RTC_WAKEUP, and the hidden flag setExactAndAllowWhileIdle()
    // passes.
    static final int RTC_WAKEUP = 0, ALLOW_WHILE_IDLE = 1 << 2;
    // Fixed request codes (job 7421's id), so setting again replaces.
    static final int REQ_FIRE = 7421, REQ_WAKE = 7422;
    static final long WAKE_LEAD_MS = 15000;

    public static void main(String[] args) throws Exception {
        try {
            if (args.length == 2 && args[0].equals("cancel")) {
                cancel(args[1]);
            } else if (args.length == 3 && args[0].equals("set")) {
                set(args[1], Long.parseLong(args[2]));
            } else {
                System.err.println("usage: TdAlarm set SHIM EPOCH_MS\n"
                        + "       TdAlarm cancel SHIM");
                System.exit(2);
            }
        } catch (InvocationTargetException e) {
            // A refusal from system_server arrives wrapped; show the reason.
            System.err.println("TdAlarm: " + e.getCause());
            System.exit(1);
        }
    }

    static void set(String shim, long at) throws Exception {
        boolean lock = at - WAKE_LEAD_MS > System.currentTimeMillis();
        schedule(at, sender(REQ_FIRE, tickIntent(shim, lock), UPDATE_CURRENT));
        PendingIntent wake = sender(REQ_WAKE, wakeIntent(), UPDATE_CURRENT);
        if (lock) {
            schedule(at - WAKE_LEAD_MS, wake);
        } else {
            call(alarms(), "remove", wake, null);
        }
    }

    static void cancel(String shim) throws Exception {
        PendingIntent[] ops = {
            sender(REQ_FIRE, tickIntent(shim, false), NO_CREATE),
            sender(REQ_WAKE, wakeIntent(), NO_CREATE),
        };
        for (PendingIntent op : ops) {
            if (op != null) {
                call(alarms(), "remove", op, null);
            }
        }
    }

    // What AlarmManager.setExactAndAllowWhileIdle() sends.
    static void schedule(long at, PendingIntent op) throws Exception {
        call(alarms(), "set", PKG, RTC_WAKEUP, at, 0L, 0L, ALLOW_WHILE_IDLE,
                op, null, null, null, null);
    }

    // TermuxService runs the shim in the background, as Termux:API's job
    // scheduler does.
    static Intent tickIntent(String shim, boolean lock) {
        Intent i = new Intent("com.termux.service_execute",
                Uri.parse("file://" + shim));
        i.setClassName(PKG, SERVICE);
        i.putExtra("com.termux.execute.background", true);
        i.putExtra("com.termux.execute.arguments",
                lock ? new String[] {"--alarm"} : new String[0]);
        return i;
    }

    // What termux-wake-lock sends.
    static Intent wakeIntent() {
        return new Intent("com.termux.service_wake_lock")
                .setClassName(PKG, SERVICE);
    }

    static PendingIntent sender(int request, Intent intent, int flags)
            throws Exception {
        int user = android.os.Process.myUid() / 100000;
        Object target = call(service("activity", "android.app.IActivityManager"),
                "getIntentSenderWithFeature", SENDER_FOREGROUND_SERVICE, PKG,
                null, null, null, request, new Intent[] {intent},
                new String[] {null}, flags | IMMUTABLE, null, user);
        if (target == null) {
            return null;
        }
        Constructor<PendingIntent> c = PendingIntent.class.getDeclaredConstructor(
                Class.forName("android.content.IIntentSender"));
        c.setAccessible(true);
        return c.newInstance(target);
    }

    static Object alarms() throws Exception {
        return service("alarm", "android.app.IAlarmManager");
    }

    static Object service(String name, String iface) throws Exception {
        IBinder b = (IBinder) Class.forName("android.os.ServiceManager")
                .getMethod("getService", String.class).invoke(null, name);
        return Class.forName(iface + "$Stub")
                .getMethod("asInterface", IBinder.class).invoke(null, b);
    }

    // Calls a hidden binder method by name and argument count.
    static Object call(Object target, String name, Object... args)
            throws Exception {
        for (Method m : target.getClass().getMethods()) {
            if (m.getName().equals(name)
                    && m.getParameterTypes().length == args.length) {
                m.setAccessible(true);
                return m.invoke(target, args);
            }
        }
        throw new NoSuchMethodException(name + " with " + args.length
                + " arguments");
    }
}
