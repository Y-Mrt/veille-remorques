package fr.veille.remorques;

import android.Manifest;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;

import androidx.annotation.NonNull;
import androidx.work.Constraints;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.text.NumberFormat;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.TimeUnit;

/**
 * Télécharge régulièrement data/annonces.json et envoie une notification
 * quand une annonce encore jamais vue apparaît.
 */
public class CheckWorker extends Worker {

    private static final String WORK = "veille-remorques-check";
    private static final String CHANNEL = "nouvelles";
    private static final int NOTIF_ID = 1;
    private static final String PREFS = "veille";
    private static final String KEY_SEEN = "seen_ids";
    private static final String KEY_INIT = "initialised";

    public CheckWorker(@NonNull Context context, @NonNull WorkerParameters params) {
        super(context, params);
    }

    static void schedule(Context ctx) {
        Constraints c = new Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build();
        // La veille publie vers 8 h 15 et 19 h 15 ; un contrôle toutes les heures suffit.
        PeriodicWorkRequest req = new PeriodicWorkRequest.Builder(CheckWorker.class, 1, TimeUnit.HOURS)
                .setConstraints(c)
                .build();
        WorkManager.getInstance(ctx).enqueueUniquePeriodicWork(WORK, ExistingPeriodicWorkPolicy.KEEP, req);
    }

    static void clearNotification(Context ctx) {
        NotificationManager nm = ctx.getSystemService(NotificationManager.class);
        if (nm != null) nm.cancel(NOTIF_ID);
    }

    @NonNull
    @Override
    public Result doWork() {
        Context ctx = getApplicationContext();
        try {
            JSONObject data = new JSONObject(download(BuildConfig.SITE_URL + "data/annonces.json?t=" + System.currentTimeMillis()));
            JSONArray ads = data.optJSONArray("annonces");
            if (ads == null) return Result.success();

            SharedPreferences p = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
            Set<String> seen = new HashSet<>(p.getStringSet(KEY_SEEN, new HashSet<>()));
            boolean initialised = p.getBoolean(KEY_INIT, false);

            Set<String> online = new HashSet<>();
            List<JSONObject> fresh = new ArrayList<>();
            for (int i = 0; i < ads.length(); i++) {
                JSONObject a = ads.getJSONObject(i);
                if (!a.optBoolean("en_ligne", true)) continue;
                String id = a.optString("id");
                online.add(id);
                if (!seen.contains(id)) fresh.add(a);
            }

            // Au tout premier passage on mémorise l'existant sans notifier.
            if (initialised && !fresh.isEmpty()) notify(ctx, fresh);

            seen.addAll(online);
            p.edit().putStringSet(KEY_SEEN, seen).putBoolean(KEY_INIT, true).apply();
            return Result.success();
        } catch (Exception e) {
            return Result.retry();
        }
    }

    private static String download(String url) throws Exception {
        HttpURLConnection con = (HttpURLConnection) new URL(url).openConnection();
        con.setConnectTimeout(15000);
        con.setReadTimeout(20000);
        con.setUseCaches(false);
        try (InputStream in = con.getInputStream()) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            return out.toString(StandardCharsets.UTF_8.name());
        } finally {
            con.disconnect();
        }
    }

    private static void notify(Context ctx, List<JSONObject> fresh) {
        if (Build.VERSION.SDK_INT >= 33
                && ctx.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            return;
        }
        NotificationManager nm = ctx.getSystemService(NotificationManager.class);
        if (nm == null) return;
        NotificationChannel ch = new NotificationChannel(CHANNEL, ctx.getString(R.string.channel_name),
                NotificationManager.IMPORTANCE_DEFAULT);
        ch.setDescription(ctx.getString(R.string.channel_desc));
        nm.createNotificationChannel(ch);

        NumberFormat euro = NumberFormat.getCurrencyInstance(Locale.FRANCE);
        euro.setMaximumFractionDigits(0);
        StringBuilder lines = new StringBuilder();
        for (JSONObject a : fresh) {
            if (lines.length() > 0) lines.append('\n');
            lines.append(a.optString("titre", "Annonce"));
            if (a.has("prix") && !a.isNull("prix")) lines.append(", ").append(euro.format(a.optDouble("prix")));
            String ville = a.optString("ville", "");
            if (!ville.isEmpty()) lines.append(", ").append(ville);
            if (a.has("distance_km") && !a.isNull("distance_km")) {
                lines.append(" (").append(Math.round(a.optDouble("distance_km"))).append(" km)");
            }
        }
        String title = fresh.size() == 1
                ? "Nouvelle remorque porte-voiture"
                : fresh.size() + " nouvelles remorques porte-voiture";

        Intent open = new Intent(ctx, MainActivity.class)
                .setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent pi = PendingIntent.getActivity(ctx, 0, open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        android.app.Notification n = new android.app.Notification.Builder(ctx, CHANNEL)
                .setSmallIcon(R.drawable.ic_notif)
                .setColor(0xFFF0A202)
                .setContentTitle(title)
                .setContentText(lines.toString().split("\n")[0])
                .setStyle(new android.app.Notification.BigTextStyle().bigText(lines.toString()))
                .setContentIntent(pi)
                .setAutoCancel(true)
                .build();
        nm.notify(NOTIF_ID, n);
    }
}
