export function UserMessageItem(props: { content: string }) {
  return (
    <div className="flex items-end justify-end px-4 py-3" data-testid="chat-message">
      <div className="max-w-[75%] rounded-2xl rounded-br-md bg-[#7E5BEF] px-4 py-2.5 text-sm text-white shadow-sm">
        {props.content}
      </div>
    </div>
  );
}

