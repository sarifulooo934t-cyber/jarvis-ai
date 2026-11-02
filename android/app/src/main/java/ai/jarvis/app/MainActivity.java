package ai.jarvis.app;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebStorage;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

/**
 * JARVIS AI - thin, fast WebView shell around the JARVIS web app.
 * Server URL is configurable, so one APK works with any deployment.
 */
public class MainActivity extends Activity {

    private static final String PREFS = "jarvis";
    private static final String KEY_URL = "server_url";
    private static final String DEFAULT_URL = "https://jarvis-ai.onrender.com";

    private WebView web;
    private ProgressBar bar;
    private FrameLayout root;
    private SharedPreferences prefs;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        if (Build.VERSION.SDK_INT >= 21) getWindow().setStatusBarColor(Color.parseColor("#050b14"));

        root = new FrameLayout(this);
        root.setBackgroundColor(Color.parseColor("#050b14"));

        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("#050b14"));
        web.setLayoutParams(new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        root.addView(web);

        bar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        bar.setMax(100);
        bar.setVisibility(View.GONE);
        FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 8);
        lp.gravity = Gravity.TOP;
        bar.setLayoutParams(lp);
        root.addView(bar);

        setContentView(root);
        setupWebView();

        if (Build.VERSION.SDK_INT >= 23
                && checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, 1);
        }

        String url = prefs.getString(KEY_URL, "");
        if (url.isEmpty()) askServerUrl();
        else load(url);
    }

    private void setupWebView() {
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setSupportZoom(false);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        if (Build.VERSION.SDK_INT >= 21) s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        if (Build.VERSION.SDK_INT >= 19) WebView.setWebContentsDebuggingEnabled(true);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return handleUrl(url);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                bar.setVisibility(View.GONE);
            }

            @Override
            public void onReceivedError(WebView view, int code, String desc, String failingUrl) {
                if (failingUrl != null && failingUrl.equals(view.getUrl())) showOffline(desc);
            }
        });

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int p) {
                bar.setVisibility(p < 100 ? View.VISIBLE : View.GONE);
                bar.setProgress(p);
            }

            // mic access for the browser's Web Speech API
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        for (String r : request.getResources()) {
                            if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(r)) {
                                request.grant(new String[]{r});
                                return;
                            }
                        }
                        request.deny();
                    }
                });
            }

            @Override
            public boolean onJsAlert(WebView v, String u, String msg, final android.webkit.JsResult res) {
                new AlertDialog.Builder(MainActivity.this)
                        .setMessage(msg)
                        .setPositiveButton("OK", new android.content.DialogInterface.OnClickListener() {
                            public void onClick(android.content.DialogInterface d, int w) { res.confirm(); }
                        })
                        .setOnCancelListener(new android.content.DialogInterface.OnCancelListener() {
                            public void onCancel(android.content.DialogInterface d) { res.cancel(); }
                        }).show();
                return true;
            }

            @Override
            public boolean onJsConfirm(WebView v, String u, String msg, final android.webkit.JsResult res) {
                new AlertDialog.Builder(MainActivity.this)
                        .setMessage(msg)
                        .setPositiveButton("Haan", new android.content.DialogInterface.OnClickListener() {
                            public void onClick(android.content.DialogInterface d, int w) { res.confirm(); }
                        })
                        .setNegativeButton("Nahi", new android.content.DialogInterface.OnClickListener() {
                            public void onClick(android.content.DialogInterface d, int w) { res.cancel(); }
                        })
                        .setOnCancelListener(new android.content.DialogInterface.OnCancelListener() {
                            public void onCancel(android.content.DialogInterface d) { res.cancel(); }
                        }).show();
                return true;
            }
        });

        // long press anywhere -> app menu
        web.setOnLongClickListener(new View.OnLongClickListener() {
            @Override
            public boolean onLongClick(View v) {
                showMenu();
                return true;
            }
        });
    }

    private boolean handleUrl(String url) {
        if (url == null) return false;
        String base = prefs.getString(KEY_URL, DEFAULT_URL);
        try {
            String host = Uri.parse(url).getHost();
            String baseHost = Uri.parse(base).getHost();
            if (host != null && baseHost != null && (host.equals(baseHost) || host.endsWith("." + baseHost))) {
                return false; // stay inside the app
            }
        } catch (Exception ignored) {
        }
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
        } catch (Exception e) {
            Toast.makeText(this, "Link khol nahi paya", Toast.LENGTH_SHORT).show();
        }
        return true;
    }

    private void load(String url) {
        String u = url.trim();
        if (!u.startsWith("http")) u = "https://" + u;
        if (u.endsWith("/")) u = u.substring(0, u.length() - 1);
        web.loadUrl(u);
    }

    private void showOffline(String desc) {
        String base = prefs.getString(KEY_URL, DEFAULT_URL);
        String html = "<html><head><meta name='viewport' content='width=device-width,initial-scale=1'>"
                + "<style>body{background:#050b14;color:#cfeaff;font-family:sans-serif;text-align:center;"
                + "padding:40px 20px}a{display:inline-block;margin-top:18px;background:#00b4ff;color:#00131f;"
                + "padding:12px 22px;border-radius:10px;text-decoration:none;font-weight:bold}"
                + "p{color:#7d9bb5;font-size:14px}</style></head><body>"
                + "<h2>Server se connect nahi hua</h2>"
                + "<p>" + (desc == null ? "" : desc) + "</p>"
                + "<p>" + base + "</p>"
                + "<a href='" + base + "'>Dobara koshish karo</a>"
                + "<p style='margin-top:26px'>Server band ho sakta hai (free hosting sleep me jaati hai). "
                + "App me kahin bhi long-press karke server URL badal sakte ho.</p>"
                + "</body></html>";
        web.loadDataWithBaseURL(base, html, "text/html", "utf-8", null);
    }

    private void askServerUrl() {
        final EditText et = new EditText(this);
        et.setHint("https://your-app.onrender.com");
        et.setInputType(InputType.TYPE_TEXT_VARIATION_URI);
        et.setText(prefs.getString(KEY_URL, ""));

        new AlertDialog.Builder(this)
                .setTitle("Server URL daalo")
                .setMessage("Jahan JARVIS server deploy kiya hai uska address. Baad me long-press se badal sakte ho.")
                .setView(et)
                .setPositiveButton("Save", new android.content.DialogInterface.OnClickListener() {
                    public void onClick(android.content.DialogInterface d, int w) {
                        String v = et.getText().toString().trim();
                        if (v.isEmpty()) {
                            Toast.makeText(MainActivity.this, "URL khaali hai", Toast.LENGTH_SHORT).show();
                            askServerUrl();
                            return;
                        }
                        prefs.edit().putString(KEY_URL, v).apply();
                        load(v);
                    }
                })
                .setNegativeButton("Cancel", null)
                .show();
    }

    private void showMenu() {
        final String[] items = {"Reload", "Server URL badlo", "App data clear karo"};
        new AlertDialog.Builder(this)
                .setTitle("JARVIS")
                .setItems(items, new android.content.DialogInterface.OnClickListener() {
                    public void onClick(android.content.DialogInterface d, int which) {
                        if (which == 0) {
                            web.reload();
                        } else if (which == 1) {
                            askServerUrl();
                        } else {
                            new AlertDialog.Builder(MainActivity.this)
                                    .setMessage("Token aur settings delete ho jayengi. Sure?")
                                    .setPositiveButton("Haan", new android.content.DialogInterface.OnClickListener() {
                                        public void onClick(android.content.DialogInterface dd, int w) {
                                            WebStorage.getInstance().deleteAllData();
                                            web.clearCache(true);
                                            prefs.edit().clear().apply();
                                            askServerUrl();
                                        }
                                    })
                                    .setNegativeButton("Nahi", null).show();
                        }
                    }
                })
                .show();
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && web.canGoBack()) {
            web.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override
    protected void onDestroy() {
        if (web != null) web.destroy();
        super.onDestroy();
    }
}
