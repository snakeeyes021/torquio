// Torquio's stand-in for Windows PowerShell's hosting library (System.Management.Automation) under Wine.
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Torquio contributors
//
// Steinberg's Install Assistant (the Setup.exe in MediaBay and other Steinberg installer zips, a .NET 4 program)
// runs a package's PowerShell pre-run script (MediaBay's preinstall.ps1) in its own process, through this
// library: PowerShell.Create(), AddScript(), Invoke(), then the Information, Warning and Error streams. Windows
// has the library; Wine and .NET 4.8 don't, so the installer couldn't run the script and skipped the package.
//
// This is not PowerShell: it doesn't interpret scripts. The only PowerShell pre-run script in Steinberg's
// installers is MediaBay's preinstall.ps1, which makes sure nothing uses MediaBay while MediaBay.msi replaces
// its files: it asks running MediaBay clients (programs that loaded mediaclient.dll, such as Dorico) to close,
// cancelling the installation if they don't, then stops MediaBay's server. For that script (recognised by the
// server's name in it), Invoke() does the same without asking: with a client running it reports an error, so
// the installer cancels the MediaBay update rather than leaving it half-installed (Wine's msi can't replace
// files that are in use, and leaves them for the next restart); otherwise it stops the server and reports
// success. Any other script is not run and reports success. Either way the installer's log says what was done.
// See docs/MEDIABAY_UPDATES.md.
//
// Only the members Steinberg's installer uses (and a few neighbours, in case a newer installer uses them) are
// here, with the names and signatures of Windows PowerShell 5.1's, so that a program built against it binds to
// them. It is installed into the Wine prefix's GAC under the identity programs reference:
// System.Management.Automation, Version=3.0.0.0, PublicKeyToken=31bf3856ad364e35. The public key is a public
// identity (Mono's framework assemblies carry the same one); the assembly is delay-signed with it, so it holds
// no signature by anyone (scripts/2-install/install_powershell_host.sh).
//
// Written in C# 5, so that the compiler of the prefix's .NET Framework 4.8 (csc.exe) can build it.

using System;
using System.Collections;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;

[assembly: AssemblyTitle("System.Management.Automation (Torquio)")]
[assembly: AssemblyDescription("Torquio's stand-in for Windows PowerShell's hosting library under Wine: reports " +
                               "success without running scripts. Not PowerShell.")]
[assembly: AssemblyProduct("Torquio")]
[assembly: AssemblyCopyright("Copyright (C) 2026 Torquio contributors. GPL-3.0-or-later.")]
[assembly: AssemblyVersion("3.0.0.0")]
[assembly: AssemblyFileVersion("0.7.0.1")]
[assembly: AssemblyInformationalVersion("torquio-powershell-host 1")]
[assembly: ComVisible(false)]

namespace System.Management.Automation
{
    public sealed class PowerShell : IDisposable
    {
        private readonly List<string> scripts = new List<string>();
        private readonly PSDataStreams streams = new PSDataStreams();
        private bool hadErrors;

        private PowerShell()
        {
        }

        public static PowerShell Create()
        {
            return new PowerShell();
        }

        public PSDataStreams Streams
        {
            get { return streams; }
        }

        public bool HadErrors
        {
            get { return hadErrors; }
        }

        public PowerShell AddScript(string script)
        {
            scripts.Add(script ?? "");
            return this;
        }

        public PowerShell AddScript(string script, bool useLocalScope)
        {
            return AddScript(script);
        }

        public PowerShell AddCommand(string cmdlet)
        {
            scripts.Add(cmdlet ?? "");
            return this;
        }

        public PowerShell AddCommand(string cmdlet, bool useLocalScope)
        {
            return AddCommand(cmdlet);
        }

        public PowerShell AddStatement()
        {
            return this;
        }

        public PowerShell AddParameters(IList parameters)
        {
            return this;
        }

        public PowerShell AddParameters(IDictionary parameters)
        {
            return this;
        }

        public PowerShell AddParameter(string parameterName, object value)
        {
            return this;
        }

        public PowerShell AddParameter(string parameterName)
        {
            return this;
        }

        public PowerShell AddArgument(object value)
        {
            return this;
        }

        // Scripts aren't interpreted (see the top of this file). Steinberg's installer writes the information
        // and error streams to its log, and fails the package if there's an error.
        public Collection<PSObject> Invoke()
        {
            foreach (string script in scripts)
            {
                if (script.IndexOf(MediaBayServer + ".exe", StringComparison.OrdinalIgnoreCase) >= 0)
                    PrepareMediaBayUpdate();
                else
                    Inform("PowerShell isn't available under Wine; script " + Digest(script) + " was not run.");
            }
            scripts.Clear();
            return new Collection<PSObject>();
        }

        private const string MediaBayServer = "SteinbergMediaBayServer";

        // What MediaBay's preinstall.ps1 does, without asking anyone to close: nothing may use MediaBay's files
        // while they're replaced.
        private void PrepareMediaBayUpdate()
        {
            List<string> clients = MediaBayClients();
            if (clients.Count > 0)
            {
                string names = string.Join(", ", clients.ToArray());
                Inform("MediaBay is in use by " + names + "; not updating it now.");
                Fail("MediaBay is in use by " + names + ". Close Dorico and Steinberg's other programs, then " +
                     "update MediaBay again.", "TorquioMediaBayInUse");
                return;
            }
            foreach (Process server in Process.GetProcessesByName(MediaBayServer))
            {
                using (server)
                {
                    try
                    {
                        Inform("Stopping MediaBay's server (process " + server.Id + ").");
                        server.Kill();
                        if (!server.WaitForExit(15000))
                        {
                            Fail("MediaBay's server didn't stop.", "TorquioMediaBayServerRunning");
                            return;
                        }
                    }
                    catch (InvalidOperationException)
                    {
                        // It had already exited
                    }
                    catch (Exception e)
                    {
                        Fail("MediaBay's server couldn't be stopped: " + e.Message, "TorquioMediaBayServerRunning");
                        return;
                    }
                }
            }
            Inform("MediaBay isn't in use; ok to install (preinstall.ps1's checks done by Torquio, not PowerShell).");
        }

        // The programs (other than this one and MediaBay's server) that have loaded MediaBay's client library
        private static List<string> MediaBayClients()
        {
            List<string> found = new List<string>();
            int self = Process.GetCurrentProcess().Id;
            foreach (Process process in Process.GetProcesses())
            {
                using (process)
                {
                    try
                    {
                        if (process.Id == self || process.Id == 0 ||
                            string.Equals(process.ProcessName, MediaBayServer, StringComparison.OrdinalIgnoreCase))
                            continue;
                        foreach (ProcessModule module in process.Modules)
                        {
                            if (string.Equals(module.ModuleName, "mediaclient.dll", StringComparison.OrdinalIgnoreCase))
                            {
                                found.Add(process.ProcessName);
                                break;
                            }
                        }
                    }
                    catch (Exception)
                    {
                        // Exited, or its modules can't be read (e.g. a 32-bit process)
                    }
                }
            }
            return found;
        }

        private void Inform(string message)
        {
            streams.Information.Add(new InformationRecord("Torquio: " + message, "Torquio"));
        }

        private void Fail(string message, string errorId)
        {
            hadErrors = true;
            streams.Error.Add(new ErrorRecord(new InvalidOperationException(message), errorId, null));
        }

        public Collection<PSObject> Invoke(IEnumerable input)
        {
            return Invoke();
        }

        public Collection<T> Invoke<T>()
        {
            Invoke();
            return new Collection<T>();
        }

        public IAsyncResult BeginInvoke()
        {
            Invoke();
            return new CompletedResult();
        }

        public PSDataCollection<PSObject> EndInvoke(IAsyncResult asyncResult)
        {
            return new PSDataCollection<PSObject>();
        }

        public void Stop()
        {
        }

        public void Dispose()
        {
        }

        // A short SHA-256 of the script, so a log says which script wasn't run
        private static string Digest(string script)
        {
            using (SHA256 sha = SHA256.Create())
            {
                byte[] hash = sha.ComputeHash(Encoding.UTF8.GetBytes(script));
                StringBuilder text = new StringBuilder("sha256:");
                for (int i = 0; i < 8; i++)
                    text.Append(hash[i].ToString("x2"));
                return text.ToString();
            }
        }

        private sealed class CompletedResult : IAsyncResult
        {
            private readonly ManualResetEvent done = new ManualResetEvent(true);

            public object AsyncState
            {
                get { return null; }
            }

            public WaitHandle AsyncWaitHandle
            {
                get { return done; }
            }

            public bool CompletedSynchronously
            {
                get { return true; }
            }

            public bool IsCompleted
            {
                get { return true; }
            }
        }
    }

    public sealed class PSDataStreams
    {
        private readonly PSDataCollection<ErrorRecord> error = new PSDataCollection<ErrorRecord>();
        private readonly PSDataCollection<WarningRecord> warning = new PSDataCollection<WarningRecord>();
        private readonly PSDataCollection<InformationRecord> information = new PSDataCollection<InformationRecord>();
        private readonly PSDataCollection<VerboseRecord> verbose = new PSDataCollection<VerboseRecord>();
        private readonly PSDataCollection<DebugRecord> debug = new PSDataCollection<DebugRecord>();

        internal PSDataStreams()
        {
        }

        public PSDataCollection<ErrorRecord> Error
        {
            get { return error; }
        }

        public PSDataCollection<WarningRecord> Warning
        {
            get { return warning; }
        }

        public PSDataCollection<InformationRecord> Information
        {
            get { return information; }
        }

        public PSDataCollection<VerboseRecord> Verbose
        {
            get { return verbose; }
        }

        public PSDataCollection<DebugRecord> Debug
        {
            get { return debug; }
        }

        public void ClearStreams()
        {
            error.Clear();
            warning.Clear();
            information.Clear();
            verbose.Clear();
            debug.Clear();
        }
    }

    public class PSDataCollection<T> : IList<T>, IList, IDisposable
    {
        private readonly List<T> items = new List<T>();

        public PSDataCollection()
        {
        }

        public T this[int index]
        {
            get { return items[index]; }
            set { items[index] = value; }
        }

        object IList.this[int index]
        {
            get { return items[index]; }
            set { items[index] = (T)value; }
        }

        public int Count
        {
            get { return items.Count; }
        }

        public bool IsReadOnly
        {
            get { return false; }
        }

        bool IList.IsFixedSize
        {
            get { return false; }
        }

        bool ICollection.IsSynchronized
        {
            get { return false; }
        }

        object ICollection.SyncRoot
        {
            get { return items; }
        }

        public void Add(T item)
        {
            items.Add(item);
        }

        int IList.Add(object value)
        {
            items.Add((T)value);
            return items.Count - 1;
        }

        public void Clear()
        {
            items.Clear();
        }

        public bool Contains(T item)
        {
            return items.Contains(item);
        }

        bool IList.Contains(object value)
        {
            return value is T && items.Contains((T)value);
        }

        public int IndexOf(T item)
        {
            return items.IndexOf(item);
        }

        int IList.IndexOf(object value)
        {
            return value is T ? items.IndexOf((T)value) : -1;
        }

        public void Insert(int index, T item)
        {
            items.Insert(index, item);
        }

        void IList.Insert(int index, object value)
        {
            items.Insert(index, (T)value);
        }

        public bool Remove(T item)
        {
            return items.Remove(item);
        }

        void IList.Remove(object value)
        {
            if (value is T)
                items.Remove((T)value);
        }

        public void RemoveAt(int index)
        {
            items.RemoveAt(index);
        }

        public void CopyTo(T[] array, int arrayIndex)
        {
            items.CopyTo(array, arrayIndex);
        }

        void ICollection.CopyTo(Array array, int index)
        {
            ((ICollection)items).CopyTo(array, index);
        }

        public Collection<T> ReadAll()
        {
            Collection<T> all = new Collection<T>(new List<T>(items));
            items.Clear();
            return all;
        }

        public void Complete()
        {
        }

        public IEnumerator<T> GetEnumerator()
        {
            return items.GetEnumerator();
        }

        IEnumerator IEnumerable.GetEnumerator()
        {
            return items.GetEnumerator();
        }

        public void Dispose()
        {
        }
    }

    public class PSObject
    {
        private readonly object baseObject;

        public PSObject()
        {
        }

        public PSObject(object obj)
        {
            baseObject = obj;
        }

        public object BaseObject
        {
            get { return baseObject; }
        }

        public object ImmediateBaseObject
        {
            get { return baseObject; }
        }

        public override string ToString()
        {
            return baseObject == null ? "" : baseObject.ToString();
        }
    }

    public class InformationRecord
    {
        private readonly object messageData;
        private readonly string source;
        private readonly DateTime timeGenerated = DateTime.Now;

        public InformationRecord(object messageData, string source)
        {
            this.messageData = messageData;
            this.source = source;
        }

        public object MessageData
        {
            get { return messageData; }
        }

        public string Source
        {
            get { return source; }
        }

        public DateTime TimeGenerated
        {
            get { return timeGenerated; }
        }

        public override string ToString()
        {
            return messageData == null ? "" : messageData.ToString();
        }
    }

    public abstract class InformationalRecord
    {
        private readonly string message;

        internal InformationalRecord(string message)
        {
            this.message = message ?? "";
        }

        public string Message
        {
            get { return message; }
        }

        public override string ToString()
        {
            return message;
        }
    }

    public class WarningRecord : InformationalRecord
    {
        public WarningRecord(string message) : base(message)
        {
        }
    }

    public class VerboseRecord : InformationalRecord
    {
        public VerboseRecord(string message) : base(message)
        {
        }
    }

    public class DebugRecord : InformationalRecord
    {
        public DebugRecord(string message) : base(message)
        {
        }
    }

    public class ErrorRecord
    {
        private readonly Exception exception;
        private readonly string errorId;
        private readonly object targetObject;

        internal ErrorRecord(Exception exception, string errorId, object targetObject)
        {
            this.exception = exception;
            this.errorId = errorId;
            this.targetObject = targetObject;
        }

        public Exception Exception
        {
            get { return exception; }
        }

        public string FullyQualifiedErrorId
        {
            get { return errorId; }
        }

        public object TargetObject
        {
            get { return targetObject; }
        }

        public override string ToString()
        {
            return exception == null ? errorId ?? "" : exception.Message;
        }
    }
}
