#!/usr/bin/env python3
import argparse
import socket
import select
import sys
import re
from typing import Tuple, Optional
import time

def parse_address(addr_str: str) -> Tuple[str, int]:
    """Parse address string in format addr:port or port"""
    if ':' in addr_str:
        host, port = addr_str.split(':')
        if '/' in port:
            port = port.split('/')[0]
        return host, int(port)
    else:
        if '/' in addr_str:
            addr_str = addr_str.split('/')[0]
        return 'localhost', int(addr_str)

def create_server(addr: str, port: int) -> socket.socket:
    """Create and bind server socket"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((addr, port))
    server.listen(1)
    return server

def format_addr(addr: Tuple[str, int]) -> str:
    """Format address tuple to string"""
    return f"{addr[0]}:{addr[1]}"

def forward_data(source: socket.socket, destination: socket.socket, source_addr: str, dest_addr: str, verbose: bool) -> bool:
    """Forward data between sockets, return False if connection is closed"""
    try:
        data = source.recv(4096)
        if not data:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Connection closed by {source_addr}")
            return False
        destination.sendall(data)
        if verbose:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Forwarded {len(data)} bytes: {source_addr} -> {dest_addr}")
        return True
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error forwarding data from {source_addr}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='TCP Port Forwarding Tool'
    )
    parser.add_argument(
        '-f', '--from', dest='source', required=True,
        help='Forward to address and port (format: addr:port/port or port)'
    )
    parser.add_argument(
        '-t', '--to', dest='target', required=True,
        help='Listen on address and port (format: addr:port/port or port)'
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='Enable verbose output including data transfer information'
    )
    
    args = parser.parse_args()
    
    # Parse source and target addresses
    forward_addr, forward_port = parse_address(args.source)  # Forward to this address
    listen_addr, listen_port = parse_address(args.target)    # Listen on this address
    
    try:
        # Create listening server
        server = create_server(listen_addr, listen_port)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Started TCP forwarding")
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Listening on {listen_addr}:{listen_port}")
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Forwarding to {forward_addr}:{forward_port}")
        
        while True:
            # Wait for client connection
            client_sock, client_addr = server.accept()
            client_str = format_addr(client_addr)
            forward_str = f"{forward_addr}:{forward_port}"
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] New connection from {client_str}")
            
            try:
                # Connect to forward server
                forward_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                forward_sock.connect((forward_addr, forward_port))
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Connected to target {forward_str}")
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Connection established: {client_str} <-> {forward_str}")
                
                # Use select for bidirectional forwarding
                while True:
                    readable, _, _ = select.select(
                        [client_sock, forward_sock], [], [], 1)
                    
                    if client_sock in readable:
                        if not forward_data(client_sock, forward_sock, client_str, forward_str, args.verbose):
                            break
                            
                    if forward_sock in readable:
                        if not forward_data(forward_sock, client_sock, forward_str, client_str, args.verbose):
                            break
                            
            except Exception as e:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Forwarding error: {e}")
            finally:
                client_sock.close()
                forward_sock.close()
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Connection closed: {client_str} <-> {forward_str}")
                
    except KeyboardInterrupt:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Shutting down...")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error: {e}")
    finally:
        server.close()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Server stopped")

if __name__ == '__main__':
    main()
