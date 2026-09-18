using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using JacRed.Infrastructure.Trackers.Bitru;
using JacRed.Models.Details;
using Xunit;

namespace JacRed.Tests.Bitru;

public class BitruBackfillCommitLoopTests : IDisposable
{
    readonly string _tempDir;

    public BitruBackfillCommitLoopTests()
    {
        _tempDir = Path.Combine(Path.GetTempPath(), "jacred-bitru-backfill-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_tempDir);
    }

    public void Dispose()
    {
        try
        {
            if (Directory.Exists(_tempDir))
                Directory.Delete(_tempDir, recursive: true);
        }
        catch { }
    }

    [Fact]
    public async Task RunAsync_TwoPagesSaved_CommitsLastCursor()
    {
        long? committed = null;
        var pages = new Queue<BitruBackfillPage>(new[]
        {
            BitruBackfillPage.Ok(DummyTorrents(2), 200, null),
            BitruBackfillPage.Ok(DummyTorrents(3), 100, null)
        });

        var progress = new BitruBackfillProgress();
        await BitruBackfillCommitLoop.RunAsync(
            maxPages: 5,
            startCursor: 300,
            fetchPage: (_, _) => Task.FromResult(pages.Count > 0 ? pages.Dequeue() : BitruBackfillPage.Halt()),
            savePage: (_, _) => Task.CompletedTask,
            commitCursor: unix => committed = unix,
            commitFinished: () => { },
            progress,
            CancellationToken.None);

        Assert.Equal(100, committed);
        Assert.Equal(2, progress.FetchedPages);
        Assert.Equal(2, progress.CommittedPages);
        Assert.Equal(5, progress.SavedCount);
        Assert.Equal(100, progress.LastCommittedCursor);
        Assert.Equal("saved 5, fetchedPages=2, committedPages=2, cursor=100", progress.FormatLog());
    }

    [Fact]
    public async Task RunAsync_CancelDuringSecondPageSave_KeepsFirstCursor()
    {
        using var cts = new CancellationTokenSource();
        long? committed = null;
        int saveCalls = 0;
        var pages = new Queue<BitruBackfillPage>(new[]
        {
            BitruBackfillPage.Ok(DummyTorrents(2), 200, null),
            BitruBackfillPage.Ok(DummyTorrents(3), 100, null)
        });

        var progress = new BitruBackfillProgress { LastCommittedCursor = 300 };

        await Assert.ThrowsAsync<OperationCanceledException>(() =>
            BitruBackfillCommitLoop.RunAsync(
                maxPages: 5,
                startCursor: 300,
                fetchPage: (_, _) => Task.FromResult(pages.Count > 0 ? pages.Dequeue() : BitruBackfillPage.Halt()),
                savePage: (_, ct) =>
                {
                    saveCalls++;
                    if (saveCalls == 2)
                    {
                        cts.Cancel();
                        ct.ThrowIfCancellationRequested();
                    }
                    return Task.CompletedTask;
                },
                commitCursor: unix => committed = unix,
                commitFinished: () => { },
                progress,
                cts.Token));

        Assert.Equal(200, committed);
        Assert.Equal(2, progress.FetchedPages);
        Assert.Equal(1, progress.CommittedPages);
        Assert.Equal(2, progress.SavedCount);
        Assert.Equal(200, progress.LastCommittedCursor);
        Assert.Equal("canceled, saved=2, fetchedPages=2, committedPages=1, cursor=200", progress.FormatCanceledLog());
    }

    [Fact]
    public async Task RunAsync_CancelDuringFirstPageSave_DoesNotWriteCursor()
    {
        using var cts = new CancellationTokenSource();
        long? committed = null;
        var progress = new BitruBackfillProgress { LastCommittedCursor = 300 };

        await Assert.ThrowsAsync<OperationCanceledException>(() =>
            BitruBackfillCommitLoop.RunAsync(
                maxPages: 5,
                startCursor: 300,
                fetchPage: (_, _) => Task.FromResult(BitruBackfillPage.Ok(DummyTorrents(2), 200, null)),
                savePage: (_, ct) =>
                {
                    cts.Cancel();
                    ct.ThrowIfCancellationRequested();
                    return Task.CompletedTask;
                },
                commitCursor: unix => committed = unix,
                commitFinished: () => { },
                progress,
                cts.Token));

        Assert.Null(committed);
        Assert.Equal(1, progress.FetchedPages);
        Assert.Equal(0, progress.CommittedPages);
        Assert.Equal(0, progress.SavedCount);
        Assert.Equal(300, progress.LastCommittedCursor);
        Assert.Equal("canceled, saved=0, fetchedPages=1, committedPages=0, cursor=300", progress.FormatCanceledLog());
    }

    [Fact]
    public async Task RunAsync_HaltOnFirstPage_DoesNotSaveOrCommit()
    {
        long? committed = null;
        bool saved = false;
        var progress = new BitruBackfillProgress { LastCommittedCursor = 300 };

        await BitruBackfillCommitLoop.RunAsync(
            maxPages: 5,
            startCursor: 300,
            fetchPage: (_, _) => Task.FromResult(BitruBackfillPage.Halt()),
            savePage: (_, _) =>
            {
                saved = true;
                return Task.CompletedTask;
            },
            commitCursor: unix => committed = unix,
            commitFinished: () => { },
            progress,
            CancellationToken.None);

        Assert.False(saved);
        Assert.Null(committed);
        Assert.Equal(0, progress.FetchedPages);
        Assert.Equal(0, progress.CommittedPages);
        Assert.Equal("no items, fetchedPages=0, committedPages=0, cursor=300", progress.FormatLog());
    }

    [Fact]
    public void WriteCursorAtomic_ReplacesExistingFile()
    {
        var path = Path.Combine(_tempDir, "bitru_backfill_cursor.txt");
        BitruBackfillCommitLoop.WriteCursorAtomic(path, 1770045331);
        BitruBackfillCommitLoop.WriteCursorAtomic(path, 1769339212);

        Assert.Equal(1769339212, BitruBackfillCommitLoop.ReadCursor(path));
        Assert.Equal("1769339212", File.ReadAllText(path));
        Assert.False(File.Exists(path + ".tmp"));
    }

    [Fact]
    public async Task RunAsync_NonEmptyPageWithoutNextCursor_WritesFinished()
    {
        bool finished = false;
        long? committed = null;
        var progress = new BitruBackfillProgress { LastCommittedCursor = 1376988004 };

        await BitruBackfillCommitLoop.RunAsync(
            maxPages: 5,
            startCursor: 1376988004,
            fetchPage: (_, _) => Task.FromResult(BitruBackfillPage.Ok(DummyTorrents(95), nextCursor: null, ids: null)),
            savePage: (_, _) => Task.CompletedTask,
            commitCursor: unix => committed = unix,
            commitFinished: () => finished = true,
            progress,
            CancellationToken.None);

        Assert.True(finished);
        Assert.True(progress.Finished);
        Assert.Null(committed);
        Assert.Equal(1, progress.FetchedPages);
        Assert.Equal(1, progress.CommittedPages);
        Assert.Equal(95, progress.SavedCount);
        Assert.Equal(1376988004, progress.LastCommittedCursor);
        Assert.Equal("saved 95, fetchedPages=1, committedPages=1, cursor=1376988004, finished", progress.FormatLog());
    }

    [Fact]
    public async Task RunAsync_HaltOnFirstPage_DoesNotWriteFinished()
    {
        bool finished = false;
        var progress = new BitruBackfillProgress { LastCommittedCursor = 300 };

        await BitruBackfillCommitLoop.RunAsync(
            maxPages: 5,
            startCursor: 300,
            fetchPage: (_, _) => Task.FromResult(BitruBackfillPage.Halt()),
            savePage: (_, _) => Task.CompletedTask,
            commitCursor: _ => { },
            commitFinished: () => finished = true,
            progress,
            CancellationToken.None);

        Assert.False(finished);
        Assert.False(progress.Finished);
    }

    [Fact]
    public void WriteFinishedAtomic_ThenIsFinished_SkipsCursor()
    {
        var path = Path.Combine(_tempDir, "bitru_backfill_cursor.txt");
        BitruBackfillCommitLoop.WriteCursorAtomic(path, 1376988004);
        Assert.False(BitruBackfillCommitLoop.IsFinished(path));
        Assert.Equal(1376988004, BitruBackfillCommitLoop.ReadCursor(path));

        BitruBackfillCommitLoop.WriteFinishedAtomic(path);

        Assert.True(BitruBackfillCommitLoop.IsFinished(path));
        Assert.Null(BitruBackfillCommitLoop.ReadCursor(path));
        Assert.Equal(BitruBackfillCommitLoop.FinishedSentinel, File.ReadAllText(path));
        Assert.False(File.Exists(path + ".tmp"));
    }

    [Fact]
    public void ReadStartCursor_MissingUnixOrFinished()
    {
        var path = Path.Combine(_tempDir, "start_cursor.txt");
        Assert.Null(BitruBackfillCommitLoop.ReadStartCursor(path));
        Assert.False(BitruBackfillCommitLoop.IsFinished(path));

        BitruBackfillCommitLoop.WriteCursorAtomic(path, 1376988004);
        Assert.Equal(1376988004, BitruBackfillCommitLoop.ReadStartCursor(path));
        Assert.False(BitruBackfillCommitLoop.IsFinished(path));

        BitruBackfillCommitLoop.WriteFinishedAtomic(path);
        Assert.True(BitruBackfillCommitLoop.IsFinished(path));
        Assert.Null(BitruBackfillCommitLoop.ReadStartCursor(path));
    }

    static List<TorrentDetails> DummyTorrents(int count)
    {
        var list = new List<TorrentDetails>(count);
        for (int i = 0; i < count; i++)
            list.Add(new TorrentDetails { title = $"t{i}" });
        return list;
    }
}
