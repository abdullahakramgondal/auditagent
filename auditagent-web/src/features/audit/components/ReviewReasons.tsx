import type { ReviewNote } from '@/api/types'

type Group = { label: string; notes: ReviewNote[] }

/** The notes grouped by document, in the order that the backend sent them. */
function groupNotes(notes: ReviewNote[]): Group[] {
  const groups: Group[] = []
  for (const note of notes) {
    const group = groups.find((g) => g.label === note.group)
    if (group) group.notes.push(note)
    else groups.push({ label: note.group, notes: [note] })
  }
  return groups
}

/** Always visible, never in a collapsed panel: this is the most important part of a review. */
export function ReviewReasons({ notes }: { notes: ReviewNote[] }) {
  return (
    <section aria-labelledby="reasons-heading" className="flex flex-col gap-3">
      <h2 id="reasons-heading" className="text-lg font-semibold">
        What a person should check
      </h2>
      <p className="text-sm text-slate-600">
        The system did not guess. Each point says what we could not confirm and what to do about it.
      </p>
      {groupNotes(notes).map((group) => (
        <div key={group.label}>
          <h3 className="text-sm font-semibold text-slate-700">{group.label}</h3>
          <ul className="mt-2 flex flex-col gap-3">
            {group.notes.map((note, index) => (
              <li
                key={`${note.title}-${index}`}
                className="rounded-xl bg-white p-4 ring-1 ring-amber-300"
              >
                <p className="font-semibold">{note.title}</p>
                <p className="mt-1 text-base">{note.what}</p>
                <p className="mt-2 text-base">
                  <span className="font-medium">What to do: </span>
                  {note.todo}
                </p>
                <details className="mt-2 text-sm text-slate-600">
                  <summary className="cursor-pointer">Technical details</summary>
                  <p className="mt-1 break-words">{note.technical}</p>
                </details>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  )
}