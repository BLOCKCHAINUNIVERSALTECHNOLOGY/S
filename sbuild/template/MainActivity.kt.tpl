// Generated SBridge host — template
package {{PACKAGE}}

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // TODO: load and run {{ENTRY}} via SBridge / SVM
        // SBridge.runAsset("{{ENTRY}}")
    }
}
