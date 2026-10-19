package {{PACKAGE}}

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity

/**
 * SBridge host — loads {{ENTRY}} when native bridge is linked.
 * Phase C scaffold: replace SBridge.run with real embedding.
 */
class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // SBridge.runAsset("{{ENTRY}}")
        android.widget.Toast.makeText(this, "S App: {{APP_NAME}}", android.widget.Toast.LENGTH_LONG).show()
    }
}
