package com.example.solventa

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun WelcomeScreen(
    modifier: Modifier = Modifier
) {
    // Column stacks elements vertically. fillMaxSize makes it full screen.
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(24.dp), // Adds space around the edge of the screen
        horizontalAlignment = Alignment.CenterHorizontally, // Centers items horizontally
        verticalArrangement = Arrangement.Center // Centers items vertically
    ) {

        // 1. Image (Placeholder icon)
        // Note: For now, we use a default Android icon.
        Icon(
            painter = painterResource(id = android.R.drawable.ic_menu_compass), // Replace with your app logo later
            contentDescription = "App Logo",
            modifier = Modifier.size(100.dp),
            tint = MaterialTheme.colorScheme.primary // Uses app's main color
        )

        // Spacer adds space between elements
        Spacer(modifier = Modifier.height(32.dp))

        // 2. Main Title
        Text(
            text = "Welcome to My App",
            fontSize = 28.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onBackground,
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(16.dp))

        // 3. Subtitle / Description
        Text(
            text = "This is a simple template for the first page of your Kotlin mobile application.",
            fontSize = 16.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(horizontal = 16.dp) // Extra side padding for text
        )

        Spacer(modifier = Modifier.height(48.dp))

        // 4. Action Button
        Button(
            onClick = {
                // TODO: Define what happens when clicked (e.g., navigate to Login)
                println("Get Started button clicked!")
            },
            modifier = Modifier.fillMaxWidth().height(50.dp) // Make button wide and tall
        ) {
            Text(
                text = "Get Started",
                fontSize = 18.sp
            )
        }
    }
}

// -- Preview Function --
// This lets you see the UI in Android Studio without running the emulator.
@Preview(showBackground = true, showSystemUi = true)
@Composable
fun WelcomeScreenPreview() {
    // Assuming your app theme is named AppTheme
    // MaterialTheme {
    WelcomeScreen()
    // }
}