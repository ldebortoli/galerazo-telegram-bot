using System;
using System.Diagnostics;
using System.IO;

internal static class GalerazoBotControlLauncher
{
    [STAThread]
    private static void Main()
    {
        string projectRoot = Directory.GetParent(AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar)).FullName;
        string scriptPath = Path.Combine(projectRoot, "control_panel.py");
        string pythonw = FindPythonw();

        Process.Start(new ProcessStartInfo
        {
            FileName = pythonw,
            Arguments = "\"" + scriptPath + "\"",
            WorkingDirectory = projectRoot,
            UseShellExecute = false,
            CreateNoWindow = true
        });
    }

    private static string FindPythonw()
    {
        string localPrograms = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string pythonRoot = Path.Combine(localPrograms, "Programs", "Python");
        if (Directory.Exists(pythonRoot))
        {
            string[] candidates = Directory.GetFiles(pythonRoot, "pythonw.exe", SearchOption.AllDirectories);
            Array.Sort(candidates, StringComparer.OrdinalIgnoreCase);
            if (candidates.Length > 0) return candidates[candidates.Length - 1];
        }

        foreach (string folder in (Environment.GetEnvironmentVariable("PATH") ?? "").Split(Path.PathSeparator))
        {
            if (string.IsNullOrWhiteSpace(folder)) continue;
            string candidate = Path.Combine(folder.Trim(), "pythonw.exe");
            if (File.Exists(candidate)) return candidate;
        }

        throw new FileNotFoundException("No se encontro pythonw.exe. Instala Python o agregalo al PATH.");
    }
}
