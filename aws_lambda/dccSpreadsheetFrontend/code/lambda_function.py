import json

def lambda_handler(event, context):
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Digital Calibration Certificate</title>
        <style>
            /* Add your CSS styles here */
        </style>
    </head>
    <body>
        <h1>Upload Calibration Spreadsheet</h1>
        <form id="uploadForm">
            <input type="file" id="xlsxFile" accept=".xlsx">
            <button type="submit">Submit</button>
        </form>
        <div id="result"></div>

<script>
    document.getElementById('uploadForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const file = document.getElementById('xlsxFile').files[0];
        if (!file) {
            document.getElementById('result').innerText = 'Please select a file.';
            return;
        }
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch('https://fznbfw3lnbxzm63colpmhx5ime0hjpmp.lambda-url.sa-east-1.on.aws/', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = 'dcc.xml';  // Fallback
                if (contentDisposition) {
                    // Robust parsing of filename from Content-Disposition
                    const parts = contentDisposition.split(';');
                    const filenamePart = parts.find(part => part.trim().startsWith('filename='));
                    if (filenamePart) {
                        filename = filenamePart.split('=')[1].trim();
                        // Remove surrounding quotes if present
                        if (filename.startsWith('"') && filename.endsWith('"')) {
                            filename = filename.slice(1, -1);
                        }
                    }
                }
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                document.getElementById('result').innerText = 'File downloaded successfully.';
            } else {
                const errorText = await response.text();
                document.getElementById('result').innerText = 'Error: ' + errorText;
            }
        } catch (error) {
            document.getElementById('result').innerText = 'Error: ' + error.message;
        }
    });
</script>

    </body>
    </html>
    """
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html',
            'Access-Control-Allow-Origin': '*'
        },
        'body': html
    }
